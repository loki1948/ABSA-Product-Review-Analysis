import { percent, sentimentLabel } from "../lib/sentiment";
import type { Sentiment } from "../types/api";
import SentimentBadge from "./SentimentBadge";

interface Props {
  sentiment: Sentiment;
  confidence: number;
}

/** The single label a traditional sentiment system gives the whole review. */
export default function SentimentCard({ sentiment, confidence }: Props) {
  return (
    <section
      aria-label="Traditional view: overall sentiment"
      className="rounded-lg border border-slate-200 bg-white p-4"
    >
      <h2 className="text-sm font-semibold text-slate-700">Traditional view</h2>
      <p className="mt-1 text-xs text-slate-500">One label for the whole review.</p>
      <div className="mt-3 flex items-center gap-3">
        <SentimentBadge sentiment={sentiment} />
        <span className="text-sm text-slate-600">{percent(confidence)} confidence</span>
      </div>
      <div
        className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100"
        role="progressbar"
        aria-label={`Confidence that the review is ${sentimentLabel(sentiment).toLowerCase()}`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(confidence * 100)}
      >
        <div className="h-full bg-slate-500" style={{ width: percent(confidence) }} />
      </div>
    </section>
  );
}
