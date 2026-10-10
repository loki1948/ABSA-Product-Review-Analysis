// Cases found by the independent review of the branch.
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { analyzeReviews, ApiError } from "../services/api";
import type { AnalysisResponse, BatchAnalysisResponse } from "../types/api";
import Batch from "./Batch";

vi.mock("../services/api", async (original) => ({
  ...(await original<typeof import("../services/api")>()),
  analyzeReviews: vi.fn(),
}));

function analysed(review: string): AnalysisResponse {
  return { id: null, review, overall_sentiment: "positive", overall_confidence: 0.9, aspects: [], created_at: null };
}
const respond = (reviews: string[]): BatchAnalysisResponse => ({ total: reviews.length, items: reviews.map(analysed) });
const lines = (count: number) => Array.from({ length: count }, (_, i) => `review ${i + 1}`).join("\n");

async function paste(text: string) {
  await userEvent.click(screen.getByLabelText(/one review per line/i));
  await userEvent.paste(text);
}

beforeEach(() => {
  vi.mocked(analyzeReviews).mockReset().mockImplementation(async (reviews) => respond(reviews));
});

describe("Batch page: re-running and leaving", () => {
  it("continues after a failure instead of sending the finished reviews again", async () => {
    vi.mocked(analyzeReviews)
      .mockImplementationOnce(async (reviews) => respond(reviews))
      .mockRejectedValueOnce(new ApiError("Cannot reach the backend.", 0));
    render(<Batch />);
    await paste(lines(25));
    await userEvent.click(screen.getByRole("button", { name: /analyze 25 reviews/i }));
    await screen.findByText("Stopped after 10 of 25 reviews.");

    await userEvent.click(screen.getByRole("button", { name: /continue with the remaining 15/i }));

    expect(await screen.findByText("Analysed 25 of 25 reviews.")).toBeInTheDocument();
    const sent = vi.mocked(analyzeReviews).mock.calls.map(([reviews]) => reviews[0]);
    expect(sent).toEqual(["review 1", "review 11", "review 11", "review 21"]);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("starts from the beginning when the reviews were changed after a stop", async () => {
    vi.mocked(analyzeReviews)
      .mockImplementationOnce(async (reviews) => respond(reviews))
      .mockRejectedValueOnce(new ApiError("Cannot reach the backend.", 0));
    render(<Batch />);
    await paste(lines(25));
    await userEvent.click(screen.getByRole("button", { name: /analyze 25 reviews/i }));
    await screen.findByText("Stopped after 10 of 25 reviews.");

    await paste("\none more review");
    expect(screen.getByRole("button", { name: /analyze 26 reviews/i })).toBeInTheDocument();
  });

  it("stops sending requests when the page is left during a run", async () => {
    let release: () => void = () => undefined;
    vi.mocked(analyzeReviews).mockImplementationOnce(
      (reviews) => new Promise((resolve) => { release = () => resolve(respond(reviews)); }),
    );
    const { unmount } = render(<Batch />);
    await paste(lines(25));
    await userEvent.click(screen.getByRole("button", { name: /analyze 25 reviews/i }));
    await waitFor(() => expect(analyzeReviews).toHaveBeenCalledTimes(1));

    unmount();
    release();
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(analyzeReviews).toHaveBeenCalledTimes(1);
  });

  it("shows that it is stopping once Cancel was pressed", async () => {
    let release: () => void = () => undefined;
    vi.mocked(analyzeReviews).mockImplementationOnce(
      (reviews) => new Promise((resolve) => { release = () => resolve(respond(reviews)); }),
    );
    render(<Batch />);
    await paste(lines(25));
    await userEvent.click(screen.getByRole("button", { name: /analyze 25 reviews/i }));
    await userEvent.click(await screen.findByRole("button", { name: /cancel/i }));
    expect(screen.getByRole("button", { name: /stopping/i })).toBeDisabled();
    release();
    expect(await screen.findByText("Stopped after 10 of 25 reviews.")).toBeInTheDocument();
  });

  it("analyses a pasted review with a comma in full", async () => {
    render(<Batch />);
    await paste("Great food, slow service.");
    await userEvent.click(screen.getByRole("button", { name: /analyze 1 review$/i }));
    await waitFor(() => expect(analyzeReviews).toHaveBeenCalledWith(["Great food, slow service."], true));
  });
});
