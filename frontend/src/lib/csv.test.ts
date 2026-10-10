import type { AnalysisResponse } from "../types/api";
import { MAX_BATCH_FILE_REVIEWS, parseCsvRows, parseReviews, toCsv } from "./csv";

describe("parseReviews", () => {
  it("reads the review column of a file with a header", () => {
    const text = "id,review,stars\n1,Great screen,5\n2,Bad battery,1\n";
    expect(parseReviews(text).reviews).toEqual(["Great screen", "Bad battery"]);
  });

  it("accepts a column named text, in any letter case", () => {
    expect(parseReviews("Text\nGreat screen\n").reviews).toEqual(["Great screen"]);
  });

  it("treats a single-column file without a header as one review per line", () => {
    expect(parseReviews("Great screen\nBad battery").reviews).toEqual([
      "Great screen",
      "Bad battery",
    ]);
  });

  it("keeps commas and line breaks inside quoted fields", () => {
    const text = 'review\n"Great screen, bad battery"\n"Line one\nline two"\n"She said ""wow"""\n';
    expect(parseReviews(text).reviews).toEqual([
      "Great screen, bad battery",
      "Line one\nline two",
      'She said "wow"',
    ]);
  });

  it("handles a file saved by Excel: byte-order mark and Windows line ends", () => {
    const text = "﻿review\r\nGreat screen\r\nBad battery\r\n";
    expect(parseReviews(text).reviews).toEqual(["Great screen", "Bad battery"]);
  });

  it("reports blank and over-long rows with their line numbers", () => {
    const long = "x".repeat(5001);
    const result = parseReviews(`review\nGood\n   \n${long}\nFine\n`);
    expect(result.reviews).toEqual(["Good", "Fine"]);
    expect(result.skipped).toEqual([
      { line: 3, reason: "blank" },
      { line: 4, reason: "longer than 5000 characters" },
    ]);
  });

  it("stops at the file limit and says so", () => {
    const text = Array.from({ length: MAX_BATCH_FILE_REVIEWS + 20 }, (_, i) => `review ${i}`).join("\n");
    const result = parseReviews(text);
    expect(result.reviews).toHaveLength(MAX_BATCH_FILE_REVIEWS);
    expect(result.truncated).toBe(true);
  });

  it("returns nothing for an empty file", () => {
    expect(parseReviews("")).toEqual({ reviews: [], skipped: [], truncated: false });
  });

  it("uses the first column when a multi-column header has no review column", () => {
    expect(parseReviews("comment,stars\nGreat screen,5\n").reviews).toEqual([
      "comment",
      "Great screen",
    ]);
  });
});

describe("toCsv", () => {
  const item: AnalysisResponse = {
    id: 1,
    review: 'The "retina" screen, wow',
    overall_sentiment: "positive",
    overall_confidence: 0.91,
    created_at: null,
    aspects: [
      { aspect: "screen", sentiment: "positive", confidence: 0.954, context: "", start: 13, end: 19 },
    ],
  };

  it("writes one row per aspect and escapes quotes and commas", () => {
    const rows = parseCsvRows(toCsv([item]));
    expect(rows[0]).toEqual(["review", "overall_sentiment", "aspect", "sentiment", "confidence"]);
    expect(rows[1]).toEqual(['The "retina" screen, wow', "positive", "screen", "positive", "0.954"]);
  });

  it("still writes a row for a review without aspects", () => {
    const rows = parseCsvRows(toCsv([{ ...item, aspects: [] }]));
    expect(rows[1]).toEqual(['The "retina" screen, wow', "positive", "", "", ""]);
  });
});

describe("parseReviews with trailing blank lines", () => {
  it("does not report empty lines at the end of the file as skipped rows", () => {
    expect(parseReviews("review\nGood screen\n\n\n")).toEqual({
      reviews: ["Good screen"],
      skipped: [],
      truncated: false,
    });
  });

  it("still reports a blank line between reviews", () => {
    expect(parseReviews("Good\n\nFine\n\n").skipped).toEqual([{ line: 2, reason: "blank" }]);
  });
});
