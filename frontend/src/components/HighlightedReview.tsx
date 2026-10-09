import { segments } from "../lib/highlight";
import { highlightClass, percent, sentimentLabel } from "../lib/sentiment";
import type { AspectResult } from "../types/api";

interface Props {
  review: string;
  aspects: AspectResult[];
}

function describe(aspect: AspectResult): string {
  return `${aspect.aspect}: ${sentimentLabel(aspect.sentiment)}, ${percent(aspect.confidence)} confidence`;
}

/** The review text with each extracted aspect marked in its sentiment's colour. */
export default function HighlightedReview({ review, aspects }: Props) {
  return (
    <p className="whitespace-pre-wrap leading-8 text-slate-900">
      {segments(review, aspects).map((segment, index) =>
        segment.aspect ? (
          <mark
            key={index}
            title={describe(segment.aspect)}
            className={`rounded px-1 py-0.5 font-medium underline decoration-2 underline-offset-4 ${highlightClass(segment.aspect.sentiment)}`}
          >
            {segment.text}
          </mark>
        ) : (
          <span key={index}>{segment.text}</span>
        ),
      )}
    </p>
  );
}
