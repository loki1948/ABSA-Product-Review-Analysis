import { readReport, type ScopeMetrics } from "../lib/modelReport";

function score(value: number | null): string {
  return value === null ? "n/a" : value.toFixed(3);
}

const COLUMNS: { header: string; hint: string; value: (s: ScopeMetrics) => number | null }[] = [
  { header: "Aspect F1", hint: "Aspect extraction, exact span match", value: (s) => s.aspectF1 },
  { header: "Precision", hint: "Aspect extraction precision", value: (s) => s.aspectPrecision },
  { header: "Recall", hint: "Aspect extraction recall", value: (s) => s.aspectRecall },
  { header: "Sentiment accuracy", hint: "Aspect sentiment, gold aspects given", value: (s) => s.sentimentAccuracy },
  { header: "Sentiment macro-F1", hint: "Average F1 over the three classes", value: (s) => s.sentimentMacroF1 },
  { header: "Mixed sentences", hint: "Sentiment accuracy where aspects of one sentence differ", value: (s) => s.mixedAccuracy },
  { header: "End-to-end F1", hint: "Aspect and sentiment both right, from raw text", value: (s) => s.endToEndF1 },
  { header: "Overall accuracy", hint: "Whole-sentence sentiment, weak labels", value: (s) => s.overallAccuracy },
];

/** Test-set metrics of the deployed models, read from the evaluation report. */
export default function ModelPerformance({ report }: { report: Record<string, unknown> }) {
  const { generatedAt, domains, scopes } = readReport(report);
  const scopeName = (scope: string) =>
    scope !== "all" ? scope : domains.length === 2 ? "Both domains" : "All test data";

  return (
    <div className="space-y-2">
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table aria-label="Model performance on the test sets" className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs text-slate-600">
            <tr>
              <th scope="col" className="px-3 py-2">Test set</th>
              <th scope="col" className="px-3 py-2">Sentences</th>
              {COLUMNS.map((column) => (
                <th key={column.header} scope="col" title={column.hint} className="px-3 py-2">
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {scopes.map((scope) => (
              <tr key={scope.scope} className="border-t border-slate-100">
                <th scope="row" className="px-3 py-2 font-medium">{scopeName(scope.scope)}</th>
                <td className="px-3 py-2 tabular-nums">{scope.testSentences ?? "n/a"}</td>
                {COLUMNS.map((column) => (
                  <td key={column.header} className="px-3 py-2 tabular-nums">
                    {score(column.value(scope))}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-500">
        SemEval-2014 Task 4 gold test set
        {domains.length > 0 && ` (${domains.join(", ")})`}.
        {generatedAt && ` Evaluated ${new Date(generatedAt).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}.`}{" "}
        Scores range from 0 to 1; hover a column heading for its meaning.
      </p>
    </div>
  );
}
