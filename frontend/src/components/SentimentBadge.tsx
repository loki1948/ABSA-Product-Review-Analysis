import { badgeClass, sentimentLabel } from "../lib/sentiment";
import type { Sentiment } from "../types/api";

/** A sentiment as a coloured pill. The word is always shown, not only the colour. */
export default function SentimentBadge({ sentiment }: { sentiment: Sentiment }) {
  return (
    <span
      className={`inline-block rounded-full border px-2 py-0.5 text-xs font-medium ${badgeClass(sentiment)}`}
    >
      {sentimentLabel(sentiment)}
    </span>
  );
}
