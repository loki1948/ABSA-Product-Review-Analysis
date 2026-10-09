import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { describeError } from "../lib/errors";
import { analyzeReview, ApiError, getHealth } from "../services/api";
import type { AnalysisResponse, HealthResponse } from "../types/api";
import Analyzer from "./Analyzer";

vi.mock("../services/api", async (original) => ({
  ...(await original<typeof import("../services/api")>()),
  analyzeReview: vi.fn(),
  getHealth: vi.fn(),
}));

const HEALTHY: HealthResponse = { status: "ok", models_loaded: true, database: true, detail: null };

const RESULT: AnalysisResponse = {
  id: 1,
  review: "The screen is gorgeous.",
  overall_sentiment: "positive",
  overall_confidence: 0.93,
  aspects: [
    { aspect: "screen", sentiment: "positive", confidence: 0.97, context: "The screen is gorgeous", start: 4, end: 10 },
  ],
  created_at: "2026-10-10T08:00:00+00:00",
};

async function typeReview(text: string) {
  const box = screen.getByLabelText(/product review/i);
  await userEvent.clear(box);
  await userEvent.type(box, text);
}

beforeEach(() => {
  vi.mocked(getHealth).mockResolvedValue(HEALTHY);
  vi.mocked(analyzeReview).mockReset();
});

describe("Analyzer page", () => {
  it("analyses the review and shows the aspects", async () => {
    vi.mocked(analyzeReview).mockResolvedValue(RESULT);
    render(<Analyzer />);
    await typeReview("The screen is gorgeous.");
    await userEvent.click(screen.getByRole("button", { name: /analyze review/i }));

    expect(await screen.findByText("screen", { selector: "mark" })).toBeInTheDocument();
    expect(analyzeReview).toHaveBeenCalledWith("The screen is gorgeous.", true);
  });

  it("sends save=false when the history box is unticked", async () => {
    vi.mocked(analyzeReview).mockResolvedValue(RESULT);
    render(<Analyzer />);
    await typeReview("Nice.");
    await userEvent.click(screen.getByRole("checkbox", { name: /save to history/i }));
    await userEvent.click(screen.getByRole("button", { name: /analyze review/i }));
    await waitFor(() => expect(analyzeReview).toHaveBeenCalledWith("Nice.", false));
  });

  it("explains how to start the backend when it cannot be reached", async () => {
    vi.mocked(analyzeReview).mockRejectedValue(new ApiError("Cannot reach the backend.", 0));
    render(<Analyzer />);
    await typeReview("Nice.");
    await userEvent.click(screen.getByRole("button", { name: /analyze review/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/cannot reach the backend/i);
    expect(alert).toHaveTextContent(/uvicorn app\.main:app/);
  });

  it("retries the same review from the error box", async () => {
    vi.mocked(analyzeReview)
      .mockRejectedValueOnce(new ApiError("Internal server error.", 500))
      .mockResolvedValueOnce(RESULT);
    render(<Analyzer />);
    await typeReview("Nice.");
    await userEvent.click(screen.getByRole("button", { name: /analyze review/i }));
    await userEvent.click(await screen.findByRole("button", { name: /try again/i }));

    expect(await screen.findByText("screen", { selector: "mark" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows the validation message for invalid input without a retry button", async () => {
    vi.mocked(analyzeReview).mockRejectedValue(new ApiError("review must not be blank", 422));
    render(<Analyzer />);
    await typeReview("x");
    await userEvent.click(screen.getByRole("button", { name: /analyze review/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("review must not be blank");
    expect(screen.queryByRole("button", { name: /try again/i })).not.toBeInTheDocument();
  });

  it("disables analysis and says why when the models are not loaded", async () => {
    vi.mocked(getHealth).mockResolvedValue({
      status: "degraded",
      models_loaded: false,
      database: true,
      detail: "No trained model in models/overall_sentiment.",
    });
    render(<Analyzer />);

    expect(await screen.findByText(/no trained model in models\/overall_sentiment/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /analyze review/i })).toBeDisabled();
  });
});

describe("describeError", () => {
  it("treats 503 as models not loaded and keeps the backend's reason", () => {
    expect(describeError(new ApiError("Models are not loaded.", 503))).toEqual({
      title: "The models are not loaded",
      message: "Models are not loaded.",
      retryable: true,
    });
  });

  it("gives 404 its own title", () => {
    expect(describeError(new ApiError("Review not found.", 404)).title).toBe("Not found");
  });

  it("falls back to a server error for anything else", () => {
    expect(describeError(new ApiError("Internal server error.", 500)).title).toBe(
      "Something went wrong on the server",
    );
    expect(describeError(new TypeError("boom")).retryable).toBe(true);
  });
});
