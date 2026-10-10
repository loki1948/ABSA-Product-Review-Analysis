// Cases found by the independent review of the branch.
import type { AnalysisResponse } from "../types/api";
import { parseCsvRows, parseReviews, toCsv } from "./csv";

describe("pasted reviews without a header", () => {
  it("keeps the whole line when a review contains commas", () => {
    expect(parseReviews("Great food, slow service.\nNice screen, bad battery, okay price", "paste").reviews).toEqual([
      "Great food, slow service.",
      "Nice screen, bad battery, okay price",
    ]);
  });

  it("does not let a stray quote swallow the following lines", () => {
    expect(parseReviews('"Amazing" they said\nIt was fine', "paste").reviews).toEqual([
      '"Amazing" they said',
      "It was fine",
    ]);
  });

  it("unwraps a line that is one quoted CSV field", () => {
    expect(parseReviews('"Great food, slow service."\n"She said ""wow"""', "paste").reviews).toEqual([
      "Great food, slow service.",
      'She said "wow"',
    ]);
  });

  it("reads the named column of an uploaded file", () => {
    expect(parseReviews('id,review\n1,"Great food, slow service."', "file").reviews).toEqual([
      "Great food, slow service.",
    ]);
  });
});

describe("toCsv and spreadsheet formulas", () => {
  const base: AnalysisResponse = {
    id: 1,
    review: "",
    overall_sentiment: "neutral",
    overall_confidence: 0.5,
    aspects: [],
    created_at: null,
  };

  it.each(["=HYPERLINK(\"http://example.test\",\"click\")", "+1+1", "-2+3", "@SUM(A1)", "\tcmd"])(
    "neutralises a cell starting with a formula character: %s",
    (review) => {
      const cell = parseCsvRows(toCsv([{ ...base, review }]))[1][0];
      expect(cell).toBe(`'${review}`);
    },
  );

  it("neutralises an aspect term too", () => {
    const item = {
      ...base,
      review: "fine",
      aspects: [{ aspect: "=cmd", sentiment: "neutral" as const, confidence: 0.5, context: "", start: 0, end: 4 }],
    };
    expect(parseCsvRows(toCsv([item]))[1][2]).toBe("'=cmd");
  });

  it("leaves ordinary text and the numeric confidence alone", () => {
    const item = {
      ...base,
      review: "Good - really good",
      aspects: [{ aspect: "screen", sentiment: "positive" as const, confidence: 0.9, context: "", start: 0, end: 4 }],
    };
    expect(parseCsvRows(toCsv([item]))[1]).toEqual(["Good - really good", "neutral", "screen", "positive", "0.9"]);
  });
});
