import { readReport } from "./modelReport";
import { percent, sentimentLabel } from "./sentiment";

function scope(f1: number) {
  return {
    test_sentences: 800,
    aspect_extraction: { precision: 0.8, recall: 0.7, f1 },
    aspect_sentiment: { accuracy: 0.77, macro: { f1: 0.73 } },
    aspect_sentiment_by_sentence_type: { mixed: { accuracy: 0.5, support: 100 } },
    overall_sentiment: { accuracy: 0.8, macro: { f1: 0.72 } },
    end_to_end: { f1: 0.61 },
  };
}

describe("readReport", () => {
  it("reads every scope of a two-domain report", () => {
    const report = readReport({
      generated_at: "2026-10-10T02:00:00+00:00",
      domains: ["laptops", "restaurants"],
      results: { all: scope(0.82), laptops: scope(0.8), restaurants: scope(0.84) },
    });
    expect(report.generatedAt).toBe("2026-10-10T02:00:00+00:00");
    expect(report.domains).toEqual(["laptops", "restaurants"]);
    expect(report.scopes.map((s) => s.scope)).toEqual(["all", "laptops", "restaurants"]);
    expect(report.scopes[0]).toMatchObject({
      testSentences: 800,
      aspectF1: 0.82,
      aspectPrecision: 0.8,
      aspectRecall: 0.7,
      sentimentAccuracy: 0.77,
      sentimentMacroF1: 0.73,
      mixedAccuracy: 0.5,
      overallAccuracy: 0.8,
      overallMacroF1: 0.72,
      endToEndF1: 0.61,
    });
  });

  it("reads the old single-scope layout and marks missing sections as null", () => {
    const old = scope(0.79) as Record<string, unknown>;
    delete old.aspect_sentiment_by_sentence_type;
    const report = readReport({ domains: ["laptops"], results: { all: old } });
    expect(report.scopes).toHaveLength(1);
    expect(report.scopes[0].mixedAccuracy).toBeNull();
    expect(report.scopes[0].aspectF1).toBe(0.79);
  });

  it("never throws on an unexpected report", () => {
    expect(readReport({})).toEqual({ generatedAt: null, domains: [], scopes: [] });
    expect(readReport({ results: "broken", domains: 7 }).scopes).toEqual([]);
    expect(readReport({ results: { all: { aspect_extraction: "n/a" } } }).scopes[0].aspectF1).toBeNull();
  });
});

describe("sentiment helpers", () => {
  it("formats a probability as a whole percentage", () => {
    expect(percent(0.954)).toBe("95%");
    expect(percent(1)).toBe("100%");
  });

  it("names each sentiment in words", () => {
    expect(sentimentLabel("negative")).toBe("Negative");
  });
});
