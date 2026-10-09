"""Utilities shared by the training and evaluation scripts."""

from __future__ import annotations

import argparse
import json
import logging
import random
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch

from app.models.batching import Feature, pad_batch
from app.paths import PROCESSED_DATA_DIR

logger = logging.getLogger("training")

DEFAULT_MODEL_NAME = "bert-base-uncased"
DOMAINS = ("laptops", "restaurants")


def set_seed(seed: int) -> None:
    """Seed every random number generator involved, for reproducible runs."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def get_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_split(
    split: str,
    domains: list[str] | None = None,
    limit: int | None = None,
    data_dir: Path = PROCESSED_DATA_DIR,
) -> list[dict[str, Any]]:
    """Load ``train`` / ``val`` / ``test`` records written by ``prepare_dataset``."""
    path = data_dir / f"{split}.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run: python -m training.prepare_dataset")
    with path.open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    if domains:
        records = [r for r in records if r["domain"] in domains]
    return records[:limit] if limit else records


def sentence_level_label(polarities: list[str]) -> str | None:
    """Derive a whole-sentence sentiment label from its aspect annotations.

    SemEval-2014 has no sentence-level sentiment labels, so the "traditional"
    overall-sentiment classifier is trained with this weak label: the majority
    of positive vs. negative aspects, ``neutral`` on a tie. Sentences without
    usable aspect annotations get no label and are not used.
    """
    usable = [p for p in polarities if p in ("positive", "negative", "neutral")]
    if not usable:
        return None
    balance = usable.count("positive") - usable.count("negative")
    return "positive" if balance > 0 else "negative" if balance < 0 else "neutral"


def add_training_args(parser: argparse.ArgumentParser, lr: float, epochs: int) -> None:
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME, help="pretrained checkpoint")
    parser.add_argument("--domains", nargs="+", default=list(DOMAINS), choices=DOMAINS)
    parser.add_argument("--epochs", type=int, default=epochs)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=lr)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--warmup-ratio", type=float, default=0.1)
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int, default=None, help="use only N sentences (smoke test)")


def _length_bucketed_batches(
    lengths: list[int], batch_size: int, rng: random.Random
) -> list[list[int]]:
    """Shuffled batches whose members have similar lengths (less padding = faster)."""
    indices = list(range(len(lengths)))
    rng.shuffle(indices)
    batches: list[list[int]] = []
    pool = batch_size * 50
    for start in range(0, len(indices), pool):
        chunk = sorted(indices[start : start + pool], key=lambda i: lengths[i])
        batches += [chunk[i : i + batch_size] for i in range(0, len(chunk), batch_size)]
    rng.shuffle(batches)
    return batches


def fine_tune(
    model: torch.nn.Module,
    features: list[Feature],
    pad_token_id: int,
    args: argparse.Namespace,
    evaluate: Callable[[], dict[str, Any]],
    selection_metric: str,
    save: Callable[[], None],
) -> dict[str, Any]:
    """Fine-tune ``model`` and keep the checkpoint that is best on validation.

    ``evaluate`` returns validation metrics after each epoch; whenever
    ``selection_metric`` improves, ``save`` is called. The test set plays no
    part here, so it stays an unbiased estimate for the final evaluation.
    """
    device = get_device()
    model.to(device)

    # Standard BERT fine-tuning recipe: AdamW, no weight decay on biases and
    # LayerNorm weights, learning rate warmed up linearly then decayed to zero.
    no_decay = ("bias", "LayerNorm.weight")
    grouped = [
        {"params": [p for n, p in model.named_parameters() if not any(k in n for k in no_decay)],
         "weight_decay": args.weight_decay},
        {"params": [p for n, p in model.named_parameters() if any(k in n for k in no_decay)],
         "weight_decay": 0.0},
    ]
    optimizer = torch.optim.AdamW(grouped, lr=args.lr)
    steps_per_epoch = -(-len(features) // args.batch_size)
    total_steps = steps_per_epoch * args.epochs
    warmup_steps = int(total_steps * args.warmup_ratio)

    def lr_factor(step: int) -> float:
        if step < warmup_steps:
            return step / max(1, warmup_steps)
        return max(0.0, (total_steps - step) / max(1, total_steps - warmup_steps))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_factor)

    rng = random.Random(args.seed)
    lengths = [len(f["input_ids"]) for f in features]
    history: list[dict[str, Any]] = []
    best_score, best_epoch, step = -1.0, 0, 0
    started = time.time()
    logger.info(
        "Training on %s: %d examples, %d epochs, %d steps", device, len(features), args.epochs, total_steps
    )

    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss, seen = 0.0, 0
        for batch_indices in _length_bucketed_batches(lengths, args.batch_size, rng):
            batch = pad_batch([features[i] for i in batch_indices], pad_token_id, device)
            loss = model(**batch).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()

            step += 1
            running_loss += loss.item() * len(batch_indices)
            seen += len(batch_indices)
            if step % 25 == 0 or step == total_steps:
                elapsed = time.time() - started
                logger.info(
                    "epoch %d  step %d/%d  loss %.4f  elapsed %.1f min  remaining ~%.1f min",
                    epoch, step, total_steps, running_loss / seen,
                    elapsed / 60, elapsed / step * (total_steps - step) / 60,
                )

        metrics = evaluate()
        score = float(metrics[selection_metric])
        entry = {"epoch": epoch, "train_loss": running_loss / max(seen, 1), "validation": metrics}
        history.append(entry)
        logger.info("epoch %d done: train_loss %.4f, val %s = %.4f",
                    epoch, entry["train_loss"], selection_metric, score)
        if score > best_score:
            best_score, best_epoch = score, epoch
            save()
            logger.info("New best checkpoint saved (epoch %d).", epoch)

    return {
        "history": history,
        "best_epoch": best_epoch,
        "selection_metric": selection_metric,
        "best_validation_score": best_score,
        "training_minutes": round((time.time() - started) / 60, 2),
        "device": str(device),
    }


def write_training_log(
    output_dir: Path, args: argparse.Namespace, result: dict[str, Any], data: dict[str, Any]
) -> None:
    payload = {
        "hyperparameters": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
        "data": data,
        "versions": {"torch": torch.__version__},
        **result,
    }
    (output_dir / "training_log.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S"
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    from transformers.utils import logging as transformers_logging

    transformers_logging.set_verbosity_error()
    transformers_logging.disable_progress_bar()
