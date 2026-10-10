import { SENTIMENTS } from "../lib/sentiment";
import type { AnalysisResponse } from "../types/api";
import AspectSentimentChart from "./AspectSentimentChart";
import AspectTable from "./AspectTable";
import HighlightedReview from "./HighlightedReview";
import SentimentCard from "./SentimentCard";
import StateMessage from "./StateMessage";

/** One sentence on what the aspect-based view adds to the single overall label. */
export function comparisonSentence(result: AnalysisResponse): string {
  const total = result.aspects.length;
  const counts = SENTIMENTS.map((sentiment) => ({
    sentiment,
    count: result.aspects.filter((a) => a.sentiment === sentiment).length,
  })).filter((c) => c.count > 0);

  if (counts.length === 1 && counts[0].sentiment === result.overall_sentiment && total > 1) {
    return (
      `Both views agree here: the review is ${result.overall_sentiment} overall ` +
      `and all ${total} aspects are ${result.overall_sentiment}.`
    );
  }
  const parts = counts.map((c) => `${c.count} ${c.sentiment}`).join(" and ");
  return (
    `A traditional system gives this review one label: ${result.overall_sentiment}. ` +
    `Aspect-based analysis finds ${parts} ${total === 1 ? "aspect" : "aspects"}.`
  );
}

/** Everything the system found in one review: the overall label, then the aspects. */
export default function AnalysisResult({ result }: { result: AnalysisResponse }) {
  const hasAspects = result.aspects.length > 0;
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <div className="min-w-0 lg:col-span-1">
        <SentimentCard
          sentiment={result.overall_sentiment}
          confidence={result.overall_confidence}
        />
      </div>
      <section
        aria-label="Aspect-based view"
        className="min-w-0 space-y-4 rounded-lg border border-slate-200 bg-white p-4 lg:col-span-2"
      >
        <div>
          <h2 className="text-sm font-semibold text-slate-700">Aspect-based view</h2>
          <p className="mt-1 text-xs text-slate-500">
            Each product aspect the review mentions, with the sentiment towards it.
          </p>
        </div>
        <HighlightedReview review={result.review} aspects={result.aspects} />
        {hasAspects ? (
          <>
            <AspectSentimentChart aspects={result.aspects} />
            <AspectTable aspects={result.aspects} />
            <p className="text-sm text-slate-700">{comparisonSentence(result)}</p>
          </>
        ) : (
          <StateMessage
            kind="empty"
            message="No product aspects were found in this review. Try a review that names parts or features of the product, such as the screen, the battery or the service."
          />
        )}
      </section>
    </div>
  );
}
