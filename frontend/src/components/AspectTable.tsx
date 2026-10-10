import { percent } from "../lib/sentiment";
import type { AspectResult } from "../types/api";
import SentimentBadge from "./SentimentBadge";

/** One row per extracted aspect. */
export default function AspectTable({ aspects }: { aspects: AspectResult[] }) {
  return (
    <div className="relative overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-600">
          <tr>
            <th scope="col" className="px-3 py-2">Aspect</th>
            <th scope="col" className="px-3 py-2">Sentiment</th>
            <th scope="col" className="px-3 py-2">Confidence</th>
            <th scope="col" className="px-3 py-2">Context</th>
          </tr>
        </thead>
        <tbody>
          {aspects.map((aspect) => (
            <tr key={`${aspect.start}-${aspect.end}`} className="border-t border-slate-100">
              <th scope="row" className="px-3 py-2 font-medium">{aspect.aspect}</th>
              <td className="px-3 py-2">
                <SentimentBadge sentiment={aspect.sentiment} />
              </td>
              <td className="px-3 py-2 tabular-nums">{percent(aspect.confidence)}</td>
              <td className="px-3 py-2 text-slate-600">{aspect.context}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
