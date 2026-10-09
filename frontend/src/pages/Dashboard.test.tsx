import { render, screen, within } from "@testing-library/react";

import { ApiError, getModelInfo, getStatistics } from "../services/api";
import type { StatisticsResponse } from "../types/api";
import Dashboard from "./Dashboard";

vi.mock("../services/api", async (original) => ({
  ...(await original<typeof import("../services/api")>()),
  getStatistics: vi.fn(),
  getModelInfo: vi.fn(),
}));

const STATISTICS: StatisticsResponse = {
  total_reviews: 4,
  total_aspects: 5,
  overall_sentiment_distribution: { positive: 2, negative: 2, neutral: 0 },
  aspect_sentiment_distribution: { positive: 3, negative: 2, neutral: 0 },
  top_aspects: [
    { aspect: "battery", total: 3, positive: 2, negative: 1, neutral: 0 },
    { aspect: "camera", total: 2, positive: 1, negative: 1, neutral: 0 },
  ],
};

const EMPTY: StatisticsResponse = {
  total_reviews: 0,
  total_aspects: 0,
  overall_sentiment_distribution: { positive: 0, negative: 0, neutral: 0 },
  aspect_sentiment_distribution: { positive: 0, negative: 0, neutral: 0 },
  top_aspects: [],
};

function scope(f1: number) {
  return {
    test_sentences: 800,
    aspect_extraction: { precision: 0.8, recall: 0.7, f1 },
    aspect_sentiment: { accuracy: 0.77, macro: { f1: 0.73 } },
    aspect_sentiment_by_sentence_type: { mixed: { accuracy: 0.5 } },
    overall_sentiment: { accuracy: 0.8, macro: { f1: 0.72 } },
    end_to_end: { f1: 0.61 },
  };
}

const REPORT = {
  report: {
    generated_at: "2026-10-10T02:00:00+00:00",
    domains: ["laptops", "restaurants"],
    results: { all: scope(0.8234), laptops: scope(0.8), restaurants: scope(0.84) },
  },
};

beforeEach(() => {
  vi.mocked(getStatistics).mockReset().mockResolvedValue(STATISTICS);
  vi.mocked(getModelInfo).mockReset().mockResolvedValue(REPORT);
});

describe("Dashboard page", () => {
  it("shows the summary numbers", async () => {
    render(<Dashboard />);
    const summary = await screen.findByRole("list", { name: /summary/i });
    const items = within(summary).getAllByRole("listitem").map((item) => item.textContent);
    expect(items).toEqual([
      "Reviews analysed4",
      "Aspect mentions5",
      "Positive reviews50%",
      "Positive aspect mentions60%",
    ]);
  });

  it("describes each chart in words", async () => {
    render(<Dashboard />);
    expect(
      await screen.findByRole("figure", { name: /overall sentiment of 4 reviews: 2 positive, 0 neutral, 2 negative/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("figure", { name: /most frequent aspects: battery \(3\), camera \(2\)/i })).toBeInTheDocument();
    expect(screen.getByRole("figure", { name: /sentiment per aspect/i })).toBeInTheDocument();
  });

  it("explains the empty dashboard instead of drawing empty charts", async () => {
    vi.mocked(getStatistics).mockResolvedValue(EMPTY);
    render(<Dashboard />);
    expect(await screen.findByText(/no reviews have been analysed yet/i)).toBeInTheDocument();
    expect(screen.queryByRole("figure")).not.toBeInTheDocument();
  });

  it("lists the model metrics for every test set", async () => {
    render(<Dashboard />);
    const table = await screen.findByRole("table", { name: /model performance/i });
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows.map((row) => within(row).getAllByRole("rowheader")[0].textContent)).toEqual([
      "Both domains",
      "laptops",
      "restaurants",
    ]);
    expect(within(rows[0]).getByText("0.823")).toBeInTheDocument();
  });

  it("keeps the charts when there is no evaluation report", async () => {
    vi.mocked(getModelInfo).mockRejectedValue(new ApiError("No evaluation report yet.", 404));
    render(<Dashboard />);
    expect(await screen.findByText(/no evaluation report yet/i)).toBeInTheDocument();
    expect(await screen.findByRole("list", { name: /summary/i })).toBeInTheDocument();
  });

  it("shows n/a for metrics an older report does not contain", async () => {
    const old = scope(0.79) as Record<string, unknown>;
    delete old.aspect_sentiment_by_sentence_type;
    vi.mocked(getModelInfo).mockResolvedValue({ report: { domains: ["laptops"], results: { all: old } } });
    render(<Dashboard />);
    const table = await screen.findByRole("table", { name: /model performance/i });
    expect(within(table).getByText("n/a")).toBeInTheDocument();
  });

  it("reports a failed statistics request with a retry", async () => {
    vi.mocked(getStatistics).mockRejectedValue(new ApiError("Cannot reach the backend.", 0));
    render(<Dashboard />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/cannot reach the backend/i);
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });
});
