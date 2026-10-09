import type { FormEvent, KeyboardEvent } from "react";

import { MAX_REVIEW_CHARS } from "../lib/csv";

export const EXAMPLES = [
  {
    label: "Laptop review",
    text: "The screen is gorgeous and the keyboard feels great, but the battery life is terrible.",
  },
  {
    label: "Restaurant review",
    text: "The pasta was delicious and the staff were friendly, although the prices are a bit high.",
  },
  {
    label: "Mixed review",
    text: "Fast processor and a solid build. The speakers are weak and the webcam is average.",
  },
];

interface Props {
  value: string;
  onChange: (value: string) => void;
  /** Whether the result is stored in the review history. */
  save: boolean;
  onSaveChange: (save: boolean) => void;
  onSubmit: () => void;
  /** A request is in flight. */
  busy: boolean;
  /** Set when analysis is unavailable; shown next to the disabled button. */
  disabledReason?: string;
}

/** The form a review is typed into. Owns no data: the page holds the text. */
export default function ReviewInput({
  value,
  onChange,
  save,
  onSaveChange,
  onSubmit,
  busy,
  disabledReason,
}: Props) {
  const canSubmit = !busy && !disabledReason && value.trim().length > 0;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (canSubmit) onSubmit();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && canSubmit) {
      event.preventDefault();
      onSubmit();
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <label htmlFor="review" className="block text-sm font-medium">
          Product review
        </label>
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
          <span>Try an example:</span>
          {EXAMPLES.map((example) => (
            <button
              key={example.label}
              type="button"
              onClick={() => onChange(example.text)}
              className="rounded-full border border-slate-300 bg-white px-2.5 py-1 hover:border-blue-600 hover:text-blue-700"
            >
              {example.label}
            </button>
          ))}
        </div>
      </div>
      <textarea
        id="review"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        rows={5}
        maxLength={MAX_REVIEW_CHARS}
        placeholder="Paste or type a product review…"
        aria-describedby="review-help"
        className="w-full rounded-md border border-slate-300 bg-white p-3 text-sm focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-200"
      />
      <div id="review-help" className="flex flex-wrap justify-between gap-2 text-xs text-slate-500">
        <span>Press Ctrl+Enter to analyze.</span>
        <span className="tabular-nums">
          {value.length} / {MAX_REVIEW_CHARS}
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-4">
        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-md bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? "Analyzing…" : "Analyze Review"}
        </button>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={save}
            onChange={(event) => onSaveChange(event.target.checked)}
            className="h-4 w-4"
          />
          Save to history
        </label>
        {disabledReason && <p className="text-sm text-amber-800">{disabledReason}</p>}
      </div>
    </form>
  );
}
