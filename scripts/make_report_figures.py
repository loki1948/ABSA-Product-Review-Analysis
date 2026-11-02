"""Draw the diagrams and training curves used by docs/project_report.md.

Run from the repository root:  .venv/Scripts/python scripts/make_report_figures.py
Output: docs/report_figures/*.png
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "report_figures"
BLUE, GREEN, ORANGE, GREY, PURPLE = "#dbe8f7", "#dcf0dc", "#fbe5cc", "#eeeeee", "#e8def5"


def box(ax, x, y, w, h, text, color, size=9, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=color, ec="#333333", lw=1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size,
            fontweight="bold" if bold else "normal")


def arrow(ax, x1, y1, x2, y2, label=None, size=7.5, both=False):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="<|-|>" if both else "-|>",
                                 mutation_scale=11, lw=1, color="#333333"))
    if label:
        ax.text((x1 + x2) / 2 + 0.08, (y1 + y2) / 2, label, fontsize=size, va="center")


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h), dpi=200)
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def save(fig, name):
    fig.savefig(OUT / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def architecture():
    fig, ax = canvas(10, 7.2)
    ax.set_xlim(-0.3, 10)
    ax.text(0.2, 6.95, "Presentation layer (browser)", fontsize=9, fontweight="bold")
    for i, name in enumerate(["Home", "Analyzer", "Batch (CSV)", "History", "Dashboard"]):
        box(ax, 0.2 + i * 1.95, 6.1, 1.75, 0.6, name, BLUE)
    box(ax, 1.6, 5.25, 6.8, 0.5,
        "API client (src/services/api.ts)   React 19 + TypeScript + Tailwind CSS + Recharts", BLUE, 8)
    arrow(ax, 5, 6.1, 5, 5.75)
    arrow(ax, 5, 5.25, 5, 4.75, "JSON over HTTP, routes under /api", both=True)
    ax.text(0.2, 4.6, "Application layer (FastAPI + Uvicorn)", fontsize=9, fontweight="bold")
    box(ax, 0.2, 3.85, 3.0, 0.6, "Analysis routes\nPOST /analyze, /analyze/batch", GREEN, 8)
    box(ax, 3.5, 3.85, 3.0, 0.6, "Review routes\nGET, DELETE /reviews; /statistics", GREEN, 8)
    box(ax, 6.8, 3.85, 3.0, 0.6, "Health routes\nGET /health, /model-info", GREEN, 8)
    ax.text(0.2, 3.45, "NLP pipeline (ABSAPipeline)", fontsize=9, fontweight="bold")
    steps = ["Preprocessing\nclean, sentences,\ntokens + offsets",
             "Aspect extraction\nBERT token classifier\nBIO tags -> spans",
             "Aspect sentiment\nBERT sentence-pair\n[CLS] s [SEP] a [SEP]",
             "Overall sentiment\nBERT single-sentence\nclassifier"]
    for i, s in enumerate(steps):
        box(ax, 0.2 + i * 2.45, 2.2, 2.2, 1.0, s, ORANGE, 8)
        if i < 3:
            arrow(ax, 0.2 + i * 2.45 + 2.2, 2.7, 0.2 + (i + 1) * 2.45, 2.7)
    arrow(ax, 1.7, 3.85, 1.3, 3.2)
    ax.text(0.2, 1.75, "Data and model storage", fontsize=9, fontweight="bold")
    box(ax, 0.2, 0.75, 3.0, 0.8, "SQLite via SQLAlchemy\nreviews 1 - * aspect_sentiments", PURPLE, 8)
    box(ax, 3.5, 0.75, 6.3, 0.8,
        "Fine-tuned BERT models (safetensors)\naspect_extraction    sentiment    overall_sentiment", PURPLE, 8)
    ax.plot([0.2, 0.02, 0.02], [4.15, 4.15, 1.15], color="#333333", lw=1)
    arrow(ax, 0.02, 1.15, 0.2, 1.15)
    ax.text(-0.02, 1.9, "store / read", fontsize=7, rotation=90, ha="right")
    ax.text(5.0, 1.75, "loaded once at start-up", fontsize=7.5)
    arrow(ax, 4.6, 1.55, 3.0, 2.2)
    arrow(ax, 6.6, 1.55, 5.6, 2.2)
    arrow(ax, 8.4, 1.55, 8.3, 2.2)
    box(ax, 0.2, 0.05, 9.6, 0.5,
        "Offline training (backend/training): prepare_dataset -> train_aspect -> train_sentiment (x2)"
        " -> evaluate, baseline, error_analysis -> promote", GREY, 7.5)
    save(fig, "fig_architecture.png")


def dataflow():
    fig, ax = canvas(10, 5.2)
    box(ax, 0.1, 2.2, 1.4, 0.8, "User", GREY, 9, True)
    procs = [(2.2, 3.7, "1.0\nValidate input\n(1 to 5,000 chars)"),
             (4.4, 3.7, "2.0\nPreprocess\n(clean, split, tokenise)"),
             (6.6, 3.7, "3.0\nExtract aspects\n(BIO tagging)"),
             (6.6, 1.6, "4.0\nClassify aspect\nsentiment"),
             (4.4, 1.6, "5.0\nClassify overall\nsentiment"),
             (2.2, 1.6, "6.0\nStore and\nrespond")]
    for x, y, t in procs:
        box(ax, x, y, 1.9, 0.95, t, ORANGE, 8)
    arrow(ax, 0.6, 3.0, 2.2, 4.4)
    ax.text(0.35, 3.85, "review text", fontsize=7)
    arrow(ax, 2.2, 3.8, 1.35, 3.0)
    ax.text(1.95, 3.1, "422 error\nif invalid", fontsize=7)
    arrow(ax, 4.1, 4.17, 4.4, 4.17)
    ax.text(3.95, 4.75, "valid text", fontsize=7)
    arrow(ax, 6.3, 4.17, 6.6, 4.17)
    ax.text(6.05, 4.75, "sentences,\ntokens", fontsize=7)
    arrow(ax, 7.55, 3.7, 7.55, 2.55, "aspect spans\n+ context")
    arrow(ax, 6.6, 2.07, 6.3, 2.07)
    ax.text(6.0, 2.7, "aspect labels", fontsize=7)
    arrow(ax, 4.4, 2.07, 4.1, 2.07)
    ax.text(3.85, 2.7, "overall label", fontsize=7)
    arrow(ax, 2.2, 2.0, 1.5, 2.4)
    ax.text(1.4, 1.75, "JSON result", fontsize=7)
    for x, y, t in [(8.75, 3.85, "D1 Aspect model"), (8.75, 1.75, "D2 Sentiment\nmodels (x2)"),
                    (2.55, 0.15, "D3 SQLite history")]:
        ax.plot([x, x + 1.2], [y + 0.65, y + 0.65], color="#333", lw=1)
        ax.plot([x, x + 1.2], [y, y], color="#333", lw=1)
        ax.text(x + 0.6, y + 0.32, t, ha="center", va="center", fontsize=7.5)
    arrow(ax, 8.75, 4.17, 8.5, 4.17)
    arrow(ax, 8.75, 2.07, 8.5, 2.07)
    ax.plot([8.62, 8.62], [2.07, 1.3], color="#333", lw=1)
    ax.plot([8.62, 5.35], [1.3, 1.3], color="#333", lw=1)
    arrow(ax, 5.35, 1.3, 5.35, 1.6)
    arrow(ax, 3.15, 1.6, 3.15, 0.8)
    ax.text(3.25, 1.2, "write rows", fontsize=7)
    save(fig, "fig_dataflow.png")


def sequence():
    actors = ["User", "React UI", "FastAPI", "ABSAPipeline", "BERT models", "SQLite"]
    fig, ax = canvas(10, 6.4)
    xs = [0.8 + i * 1.7 for i in range(len(actors))]
    for x, a in zip(xs, actors):
        box(ax, x - 0.65, 5.75, 1.3, 0.45, a, BLUE, 8.5, True)
        ax.plot([x, x], [0.2, 5.75], ls="--", color="#888", lw=0.8)
    msgs = [(0, 1, "types review, presses Analyze"), (1, 2, "POST /api/analyze {review}"),
            (2, 2, "validate (Pydantic)"), (2, 3, "analyze(review)"), (3, 3, "clean, split, tokenise"),
            (3, 4, "tag tokens (aspect model)"), (4, 3, "BIO tags -> aspect spans"),
            (3, 4, "classify each (sentence, aspect)"), (3, 4, "classify each sentence (overall)"),
            (4, 3, "labels + probabilities"), (3, 2, "AnalysisResult"), (2, 5, "INSERT review + aspects"),
            (5, 2, "review id"), (2, 1, "200 OK, JSON"), (1, 0, "highlighted text, table, overall badge")]
    y = 5.45
    for a, b, t in msgs:
        if a == b:
            ax.plot([xs[a], xs[a] + 0.3, xs[a] + 0.3], [y, y, y - 0.15], color="#333", lw=0.9)
            arrow(ax, xs[a] + 0.3, y - 0.15, xs[a] + 0.02, y - 0.15)
            ax.text(xs[a] + 0.4, y - 0.07, t, fontsize=7, va="center")
        else:
            arrow(ax, xs[a], y, xs[b], y)
            ax.text((xs[a] + xs[b]) / 2, y + 0.07, t, fontsize=7, ha="center")
        y -= 0.35
    save(fig, "fig_sequence.png")


def usecase():
    fig, ax = canvas(10, 4.6)
    ax.add_patch(FancyBboxPatch((2.2, 0.1), 6.2, 4.35, boxstyle="round,pad=0.02", fc="white", ec="#333"))
    ax.text(5.3, 4.2, "ABSA web application", ha="center", fontsize=9, fontweight="bold")
    for x, y, who in [(0.9, 2.6, "Analyst /\nseller"), (9.3, 1.2, "Developer")]:
        ax.add_patch(plt.Circle((x, y + 0.65), 0.15, fc="white", ec="#333"))
        ax.plot([x, x], [y + 0.5, y + 0.1], color="#333")
        ax.plot([x - 0.2, x + 0.2], [y + 0.35, y + 0.35], color="#333")
        ax.plot([x, x - 0.18], [y + 0.1, y - 0.2], color="#333")
        ax.plot([x, x + 0.18], [y + 0.1, y - 0.2], color="#333")
        ax.text(x, y - 0.5, who, ha="center", fontsize=8)
    cases = [(3.6, 3.6, "Analyse one review"), (3.6, 2.85, "Analyse a CSV or pasted batch"),
             (3.6, 2.1, "Export results to CSV"), (3.6, 1.35, "Browse or delete history"),
             (3.6, 0.6, "View dashboard statistics"), (6.9, 3.2, "View model test metrics"),
             (6.9, 2.0, "Check service health"), (6.9, 0.8, "Retrain and promote models")]
    for x, y, t in cases:
        ax.add_patch(Ellipse((x, y), 2.5, 0.55, fc=GREEN, ec="#333"))
        ax.text(x, y, t, ha="center", va="center", fontsize=7.5)
        if x < 5 or t.startswith("View model"):
            ax.plot([1.1, x - 1.25], [3.0, y], color="#555", lw=0.7)
        if x > 5:
            ax.plot([9.1, x + 1.25], [1.6, y], color="#555", lw=0.7)
    save(fig, "fig_usecase.png")


def curves():
    specs = [("aspect_extraction", "Aspect extraction", "f1", "validation span F1"),
             ("sentiment", "Aspect sentiment", "macro_f1", "validation macro-F1"),
             ("overall_sentiment", "Overall sentiment", "macro_f1", "validation macro-F1")]
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.3), dpi=200)
    for ax, (folder, title, key, label) in zip(axes, specs):
        log = json.loads((ROOT / "models" / folder / "training_log.json").read_text())
        ep = [h["epoch"] for h in log["history"]]
        loss = [h["train_loss"] for h in log["history"]]
        val = [h["validation"][key] for h in log["history"]]
        ax.plot(ep, loss, "o-", color="#1f77b4")
        ax.set_xlabel("epoch")
        ax.set_ylabel("training loss", color="#1f77b4")
        ax.set_xticks(ep)
        ax2 = ax.twinx()
        ax2.plot(ep, val, "s--", color="#d62728")
        ax2.set_ylabel(label, color="#d62728")
        ax2.set_ylim(0.55, 0.9)
        best = log["best_epoch"]
        ax2.axvline(best, color="#999", lw=0.8, ls=":")
        ax2.text(best, 0.565, " kept", fontsize=7, color="#555")
        ax.set_title(title, fontsize=10)
    fig.tight_layout()
    save(fig, "fig_training_curves.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    architecture()
    dataflow()
    sequence()
    usecase()
    curves()
    print("written to", OUT)
