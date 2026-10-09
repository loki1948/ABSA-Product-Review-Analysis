// Reads models/evaluation_report.json as served by GET /api/model-info.
//
// The evaluation script owns that file's layout and it has changed before, so
// nothing here assumes a field exists: whatever is missing becomes null and
// the interface shows "n/a".

export interface ScopeMetrics {
  /** "all", or a single test domain such as "laptops". */
  scope: string;
  testSentences: number | null;
  aspectPrecision: number | null;
  aspectRecall: number | null;
  aspectF1: number | null;
  sentimentAccuracy: number | null;
  sentimentMacroF1: number | null;
  /** Accuracy on aspects in sentences that mix sentiments. */
  mixedAccuracy: number | null;
  overallAccuracy: number | null;
  overallMacroF1: number | null;
  endToEndF1: number | null;
}

export interface ModelReport {
  generatedAt: string | null;
  domains: string[];
  scopes: ScopeMetrics[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function numberAt(source: unknown, ...path: string[]): number | null {
  let value = source;
  for (const key of path) {
    if (!isRecord(value)) return null;
    value = value[key];
  }
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function readReport(report: Record<string, unknown>): ModelReport {
  const results = isRecord(report.results) ? report.results : {};
  return {
    generatedAt: typeof report.generated_at === "string" ? report.generated_at : null,
    domains: Array.isArray(report.domains)
      ? report.domains.filter((d): d is string => typeof d === "string")
      : [],
    scopes: Object.entries(results).map(([scope, values]) => ({
      scope,
      testSentences: numberAt(values, "test_sentences"),
      aspectPrecision: numberAt(values, "aspect_extraction", "precision"),
      aspectRecall: numberAt(values, "aspect_extraction", "recall"),
      aspectF1: numberAt(values, "aspect_extraction", "f1"),
      sentimentAccuracy: numberAt(values, "aspect_sentiment", "accuracy"),
      sentimentMacroF1: numberAt(values, "aspect_sentiment", "macro", "f1"),
      mixedAccuracy: numberAt(values, "aspect_sentiment_by_sentence_type", "mixed", "accuracy"),
      overallAccuracy: numberAt(values, "overall_sentiment", "accuracy"),
      overallMacroF1: numberAt(values, "overall_sentiment", "macro", "f1"),
      endToEndF1: numberAt(values, "end_to_end", "f1"),
    })),
  };
}
