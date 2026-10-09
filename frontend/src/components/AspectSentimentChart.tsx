import { chartColor, SENTIMENTS, sentimentLabel } from "../lib/sentiment";
import type { AspectResult } from "../types/api";

/** How one review's aspects divide into positive, neutral and negative. */
export default function AspectSentimentChart({ aspects }: { aspects: AspectResult[] }) {
  const counts = SENTIMENTS.map((sentiment) => ({
    sentiment,
    count: aspects.filter((a) => a.sentiment === sentiment).length,
  }));
  const summary = counts.map((c) => `${c.count} ${c.sentiment}`).join(", ");

  return (
    <div>
      <div
        role="img"
        aria-label={`Aspect sentiments: ${summary}`}
        className="flex h-4 overflow-hidden rounded-full bg-slate-100"
      >
        {counts.map(
          (c) =>
            c.count > 0 && (
              <div
                key={c.sentiment}
                style={{ flexGrow: c.count, backgroundColor: chartColor(c.sentiment) }}
              />
            ),
        )}
      </div>
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600">
        {counts.map((c) => (
          <li key={c.sentiment} className="flex items-center gap-1.5">
            <span
              aria-hidden="true"
              className="h-2.5 w-2.5 rounded-sm"
              style={{ backgroundColor: chartColor(c.sentiment) }}
            />
            {sentimentLabel(c.sentiment)}: {c.count}
          </li>
        ))}
      </ul>
    </div>
  );
}
