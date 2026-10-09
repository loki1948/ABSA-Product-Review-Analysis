import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { parseCsvRows } from "../lib/csv";
import { analyzeReviews, ApiError } from "../services/api";
import type { AnalysisResponse, BatchAnalysisResponse } from "../types/api";
import Batch from "./Batch";

vi.mock("../services/api", async (original) => ({
  ...(await original<typeof import("../services/api")>()),
  analyzeReviews: vi.fn(),
}));

function analysed(review: string): AnalysisResponse {
  return {
    id: null,
    review,
    overall_sentiment: "positive",
    overall_confidence: 0.9,
    aspects: [{ aspect: "screen", sentiment: "positive", confidence: 0.95, context: review, start: 0, end: 6 }],
    created_at: null,
  };
}

function respond(reviews: string[]): BatchAnalysisResponse {
  return { total: reviews.length, items: reviews.map(analysed) };
}

const lines = (count: number) => Array.from({ length: count }, (_, i) => `screen review ${i + 1}`).join("\n");

async function paste(text: string) {
  const box = screen.getByLabelText(/one review per line/i);
  await userEvent.click(box);
  await userEvent.paste(text);
}

let downloaded: Blob | null;

beforeEach(() => {
  downloaded = null;
  vi.mocked(analyzeReviews).mockReset().mockImplementation(async (reviews) => respond(reviews));
  vi.stubGlobal("URL", {
    ...URL,
    createObjectURL: (blob: Blob) => {
      downloaded = blob;
      return "blob:test";
    },
    revokeObjectURL: () => undefined,
  });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("Batch page", () => {
  it("sends the reviews in chunks of ten, in order, and lists every result", async () => {
    render(<Batch />);
    await paste(lines(25));
    await userEvent.click(screen.getByRole("button", { name: /analyze 25 reviews/i }));

    expect(await screen.findByText("Analysed 25 of 25 reviews.")).toBeInTheDocument();
    const calls = vi.mocked(analyzeReviews).mock.calls;
    expect(calls.map(([reviews]) => reviews.length)).toEqual([10, 10, 5]);
    expect(calls[0][0][0]).toBe("screen review 1");
    expect(calls[2][0][4]).toBe("screen review 25");
    expect(within(screen.getByRole("table")).getAllByRole("row")).toHaveLength(26);
  });

  it("reports rows that cannot be analysed before anything is sent", async () => {
    render(<Batch />);
    await paste("Good screen\n   \nBad battery");
    expect(screen.getByRole("button", { name: /analyze 2 reviews/i })).toBeInTheDocument();
    expect(screen.getByText(/1 row skipped/i)).toBeInTheDocument();
    expect(screen.getByText(/line 2: blank/i)).toBeInTheDocument();
    expect(analyzeReviews).not.toHaveBeenCalled();
  });

  it("reads the review column of an uploaded CSV file", async () => {
    render(<Batch />);
    const file = new File(['id,review\n1,"Great screen, bad battery"\n2,Nice keyboard\n'], "reviews.csv", {
      type: "text/csv",
    });
    await userEvent.upload(screen.getByLabelText(/upload a csv file/i), file);
    await userEvent.click(await screen.findByRole("button", { name: /analyze 2 reviews/i }));
    await waitFor(() =>
      expect(analyzeReviews).toHaveBeenCalledWith(["Great screen, bad battery", "Nice keyboard"], true),
    );
  });

  it("stops after the running chunk when cancelled", async () => {
    let release: (value: BatchAnalysisResponse) => void = () => undefined;
    vi.mocked(analyzeReviews).mockImplementationOnce(
      (reviews) =>
        new Promise((resolve) => {
          release = () => resolve(respond(reviews));
        }),
    );
    render(<Batch />);
    await paste(lines(25));
    await userEvent.click(screen.getByRole("button", { name: /analyze 25 reviews/i }));
    await userEvent.click(await screen.findByRole("button", { name: /cancel/i }));
    release(respond([]));

    expect(await screen.findByText("Stopped after 10 of 25 reviews.")).toBeInTheDocument();
    expect(analyzeReviews).toHaveBeenCalledTimes(1);
  });

  it("keeps the results received before a failed chunk", async () => {
    vi.mocked(analyzeReviews)
      .mockImplementationOnce(async (reviews) => respond(reviews))
      .mockImplementationOnce(async (reviews) => respond(reviews))
      .mockRejectedValueOnce(new ApiError("Cannot reach the backend.", 0));
    render(<Batch />);
    await paste(lines(25));
    await userEvent.click(screen.getByRole("button", { name: /analyze 25 reviews/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/cannot reach the backend/i);
    expect(screen.getByText("Stopped after 20 of 25 reviews.")).toBeInTheDocument();
    expect(within(screen.getByRole("table")).getAllByRole("row")).toHaveLength(21);
  });

  it("downloads the results as CSV with one row per aspect", async () => {
    render(<Batch />);
    await paste("Good screen\nBad battery");
    await userEvent.click(screen.getByRole("button", { name: /analyze 2 reviews/i }));
    await userEvent.click(await screen.findByRole("button", { name: /download results/i }));

    expect(downloaded).not.toBeNull();
    const rows = parseCsvRows(await downloaded!.text());
    expect(rows[0]).toEqual(["review", "overall_sentiment", "aspect", "sentiment", "confidence"]);
    expect(rows.slice(1).map((row) => row[0])).toEqual(["Good screen", "Bad battery"]);
  });

  it("honours the save-to-history choice", async () => {
    render(<Batch />);
    await paste("Good screen");
    await userEvent.click(screen.getByRole("checkbox", { name: /save to history/i }));
    await userEvent.click(screen.getByRole("button", { name: /analyze 1 review$/i }));
    await waitFor(() => expect(analyzeReviews).toHaveBeenCalledWith(["Good screen"], false));
  });
});
