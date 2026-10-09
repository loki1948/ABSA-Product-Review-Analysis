import { render, screen, within } from "@testing-library/react";

import type { AnalysisResponse, AspectResult, Sentiment } from "../types/api";
import AnalysisResult, { comparisonSentence } from "./AnalysisResult";

const REVIEW = "The screen is gorgeous and the keyboard feels great, but the battery life is terrible.";

function aspect(term: string, sentiment: Sentiment, confidence: number): AspectResult {
  const start = REVIEW.indexOf(term);
  return { aspect: term, sentiment, confidence, context: `about the ${term}`, start, end: start + term.length };
}

function result(aspects: AspectResult[], overall: Sentiment = "neutral"): AnalysisResponse {
  return {
    id: 7,
    review: REVIEW,
    overall_sentiment: overall,
    overall_confidence: 0.612,
    aspects,
    created_at: "2026-10-10T08:00:00+00:00",
  };
}

const MIXED = result([
  aspect("screen", "positive", 0.97),
  aspect("keyboard", "positive", 0.9),
  aspect("battery life", "negative", 0.954),
]);

describe("AnalysisResult", () => {
  it("shows the overall sentiment with its confidence", () => {
    render(<AnalysisResult result={MIXED} />);
    const card = screen.getByRole("region", { name: /traditional/i });
    expect(within(card).getByText("Neutral")).toBeInTheDocument();
    expect(within(card).getByText(/61%/)).toBeInTheDocument();
  });

  it("marks every aspect inside the review text and names its sentiment", () => {
    render(<AnalysisResult result={MIXED} />);
    const mark = screen.getByText("battery life", { selector: "mark" });
    expect(mark).toHaveAttribute("title", "battery life: Negative, 95% confidence");
    expect(screen.getAllByText(/./, { selector: "mark" })).toHaveLength(3);
  });

  it("lists one table row per aspect with sentiment, confidence and context", () => {
    render(<AnalysisResult result={MIXED} />);
    const rows = within(screen.getByRole("table")).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(3);
    const battery = rows[2];
    expect(within(battery).getByText("battery life")).toBeInTheDocument();
    expect(within(battery).getByText("Negative")).toBeInTheDocument();
    expect(within(battery).getByText("95%")).toBeInTheDocument();
    expect(within(battery).getByText("about the battery life")).toBeInTheDocument();
  });

  it("summarises how many aspects have each sentiment", () => {
    render(<AnalysisResult result={MIXED} />);
    const chart = screen.getByRole("img", { name: /2 positive, 0 neutral, 1 negative/i });
    expect(chart).toBeInTheDocument();
  });

  it("still shows the overall sentiment when no aspects were found", () => {
    render(<AnalysisResult result={result([], "positive")} />);
    expect(screen.getByText(/no product aspects were found/i)).toBeInTheDocument();
    expect(screen.getByText("Positive")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});

describe("comparisonSentence", () => {
  it("contrasts one overall label with mixed aspect sentiments", () => {
    expect(comparisonSentence(MIXED)).toBe(
      "A traditional system gives this review one label: neutral. " +
        "Aspect-based analysis finds 2 positive and 1 negative aspects.",
    );
  });

  it("says so when both views agree", () => {
    const uniform = result([aspect("screen", "positive", 0.9), aspect("keyboard", "positive", 0.9)], "positive");
    expect(comparisonSentence(uniform)).toBe(
      "Both views agree here: the review is positive overall and all 2 aspects are positive.",
    );
  });

  it("uses the singular for a single aspect", () => {
    expect(comparisonSentence(result([aspect("screen", "negative", 0.9)], "positive"))).toBe(
      "A traditional system gives this review one label: positive. " +
        "Aspect-based analysis finds 1 negative aspect.",
    );
  });
});
