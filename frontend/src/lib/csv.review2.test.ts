// Cases found by the second independent review.
import { parseReviews } from "./csv";

describe("an uploaded file is always read as CSV", () => {
  it("uses the first column when no column is named review or text", () => {
    expect(parseReviews("Review Text,Rating\nGreat laptop,5\n", "file").reviews).toEqual([
      "Review Text",
      "Great laptop",
    ]);
    expect(parseReviews("id,comment\n1,Great laptop\n", "file").reviews).toEqual(["id", "1"]);
  });

  it("unquotes fields and drops other columns in a headerless file", () => {
    expect(parseReviews('"Great food, slow service.",5\n', "file").reviews).toEqual([
      "Great food, slow service.",
    ]);
  });

  it("keeps a quoted multi-line field together in a headerless file", () => {
    expect(parseReviews('"Line one\nline two"\nNext review\n', "file").reviews).toEqual([
      "Line one\nline two",
      "Next review",
    ]);
  });
});

describe("pasted text is always one review per line", () => {
  it("does not treat a first line that mentions text or review as a header", () => {
    const pasted = "Text, calls and battery are fine.\nGreat food, slow service.";
    expect(parseReviews(pasted, "paste").reviews).toEqual([
      "Text, calls and battery are fine.",
      "Great food, slow service.",
    ]);
    expect(parseReviews("Review\nThe screen is great", "paste").reviews).toEqual([
      "Review",
      "The screen is great",
    ]);
  });

  it("keeps quotes that are part of the sentence", () => {
    expect(parseReviews('"Wow" and "amazing"', "paste").reviews).toEqual(['"Wow" and "amazing"']);
  });

  it("still unwraps a line that is exactly one quoted field", () => {
    expect(parseReviews('"She said ""wow"", twice"', "paste").reviews).toEqual(['She said "wow", twice']);
  });
});
