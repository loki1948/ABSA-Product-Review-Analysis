import type { AspectResult } from "../types/api";
import { segments } from "./highlight";

function aspect(review: string, term: string, from = 0): AspectResult {
  const start = review.indexOf(term, from);
  return {
    aspect: term,
    sentiment: "positive",
    confidence: 0.9,
    context: review,
    start,
    end: start + term.length,
  };
}

const REVIEW = "Great camera, but the battery life is terrible.";

describe("segments", () => {
  it("returns the whole review as one plain segment when there are no aspects", () => {
    expect(segments(REVIEW, [])).toEqual([{ text: REVIEW, aspect: null }]);
  });

  it("splits the review around each aspect, in text order", () => {
    const camera = aspect(REVIEW, "camera");
    const battery = aspect(REVIEW, "battery life");
    const result = segments(REVIEW, [battery, camera]);
    expect(result.map((s) => s.text)).toEqual([
      "Great ",
      "camera",
      ", but the ",
      "battery life",
      " is terrible.",
    ]);
    expect(result.map((s) => s.aspect?.aspect ?? null)).toEqual([
      null,
      "camera",
      null,
      "battery life",
      null,
    ]);
  });

  it("handles aspects at the very start and very end", () => {
    const text = "Screen and keyboard";
    const result = segments(text, [aspect(text, "Screen"), aspect(text, "keyboard")]);
    expect(result.map((s) => s.text)).toEqual(["Screen", " and ", "keyboard"]);
  });

  it("keeps adjacent aspects separate", () => {
    const text = "batteryscreen";
    const result = segments(text, [aspect(text, "battery"), aspect(text, "screen")]);
    expect(result.map((s) => s.text)).toEqual(["battery", "screen"]);
    expect(result.every((s) => s.aspect !== null)).toBe(true);
  });

  it("always reproduces the review when the segments are joined", () => {
    const result = segments(REVIEW, [aspect(REVIEW, "camera"), aspect(REVIEW, "battery life")]);
    expect(result.map((s) => s.text).join("")).toBe(REVIEW);
  });

  it("ignores aspects whose offsets are outside the text or empty", () => {
    const camera = aspect(REVIEW, "camera");
    const bad: AspectResult[] = [
      { ...camera, start: -3, end: 2 },
      { ...camera, start: 40, end: 400 },
      { ...camera, start: 10, end: 10 },
      { ...camera, start: 12, end: 8 },
    ];
    expect(segments(REVIEW, bad)).toEqual([{ text: REVIEW, aspect: null }]);
  });

  it("drops an aspect that overlaps an earlier one", () => {
    const battery = aspect(REVIEW, "battery life");
    const overlapping = { ...battery, aspect: "life is", start: battery.start + 8, end: battery.end + 3 };
    const result = segments(REVIEW, [battery, overlapping]);
    expect(result.filter((s) => s.aspect).map((s) => s.text)).toEqual(["battery life"]);
    expect(result.map((s) => s.text).join("")).toBe(REVIEW);
  });
});
