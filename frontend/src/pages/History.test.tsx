import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { ApiError, deleteReview, getReviews } from "../services/api";
import type { AnalysisResponse, ReviewListResponse } from "../types/api";
import History from "./History";

vi.mock("../services/api", async (original) => ({
  ...(await original<typeof import("../services/api")>()),
  getReviews: vi.fn(),
  deleteReview: vi.fn(),
}));

function review(id: number): AnalysisResponse {
  const text = `Review number ${id}: the screen is great.`;
  return {
    id,
    review: text,
    overall_sentiment: id % 2 ? "positive" : "negative",
    overall_confidence: 0.9,
    aspects: [
      { aspect: "screen", sentiment: "positive", confidence: 0.95, context: "the screen is great", start: text.indexOf("screen"), end: text.indexOf("screen") + 6 },
    ],
    created_at: "2026-10-10T08:00:00+00:00",
  };
}

function page(ids: number[], total: number, offset = 0): ReviewListResponse {
  return { total, limit: 10, offset, items: ids.map(review) };
}

function renderAt(url = "/history") {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <History />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(getReviews).mockReset();
  vi.mocked(deleteReview).mockReset().mockResolvedValue(undefined);
});

describe("History page", () => {
  it("lists the stored reviews with their overall sentiment and aspect count", async () => {
    vi.mocked(getReviews).mockResolvedValue(page([3, 2], 2));
    renderAt();
    const rows = within(await screen.findByRole("table")).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(2);
    expect(within(rows[0]).getByText(/Review number 3/)).toBeInTheDocument();
    expect(within(rows[0]).getByText("Positive")).toBeInTheDocument();
    expect(within(rows[0]).getByText("1 aspect")).toBeInTheDocument();
    expect(getReviews).toHaveBeenCalledWith({ limit: 10, offset: 0, sentiment: undefined });
  });

  it("says so when there is no history yet", async () => {
    vi.mocked(getReviews).mockResolvedValue(page([], 0));
    renderAt();
    expect(await screen.findByText(/no reviews have been analysed yet/i)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("requests only the chosen sentiment and returns to the first page", async () => {
    vi.mocked(getReviews).mockResolvedValue(page([3, 2], 25, 10));
    renderAt("/history?page=2");
    await screen.findByRole("table");
    await userEvent.selectOptions(screen.getByLabelText(/overall sentiment/i), "negative");
    await waitFor(() =>
      expect(getReviews).toHaveBeenLastCalledWith({ limit: 10, offset: 0, sentiment: "negative" }),
    );
  });

  it("pages through the history", async () => {
    vi.mocked(getReviews).mockResolvedValue(page([37, 36], 37));
    renderAt();
    expect(await screen.findByText("1–10 of 37")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: /next/i }));
    await waitFor(() =>
      expect(getReviews).toHaveBeenLastCalledWith({ limit: 10, offset: 10, sentiment: undefined }),
    );
  });

  it("opens a review's full analysis", async () => {
    vi.mocked(getReviews).mockResolvedValue(page([3], 1));
    renderAt();
    await userEvent.click(await screen.findByRole("button", { name: /view analysis of review 3/i }));
    expect(screen.getByText("screen", { selector: "mark" })).toBeInTheDocument();
  });

  it("deletes only after confirmation, then reloads", async () => {
    vi.mocked(getReviews).mockResolvedValue(page([3, 2], 2));
    renderAt();
    await userEvent.click(await screen.findByRole("button", { name: /delete review 3/i }));
    const dialog = screen.getByRole("dialog");
    expect(deleteReview).not.toHaveBeenCalled();

    await userEvent.click(within(dialog).getByRole("button", { name: /cancel/i }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(deleteReview).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: /delete review 3/i }));
    await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: /^delete$/i }));
    await waitFor(() => expect(deleteReview).toHaveBeenCalledWith(3));
    await waitFor(() => expect(getReviews).toHaveBeenCalledTimes(2));
  });

  it("steps back a page after deleting the last review on it", async () => {
    vi.mocked(getReviews).mockResolvedValue(page([1], 21, 20));
    renderAt("/history?page=3");
    await userEvent.click(await screen.findByRole("button", { name: /delete review 1/i }));
    await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: /^delete$/i }));
    await waitFor(() =>
      expect(getReviews).toHaveBeenLastCalledWith({ limit: 10, offset: 10, sentiment: undefined }),
    );
  });

  it("shows why the history could not be loaded and offers a retry", async () => {
    vi.mocked(getReviews)
      .mockRejectedValueOnce(new ApiError("Cannot reach the backend.", 0))
      .mockResolvedValueOnce(page([3], 1));
    renderAt();
    expect(await screen.findByRole("alert")).toHaveTextContent(/cannot reach the backend/i);
    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(await screen.findByRole("table")).toBeInTheDocument();
  });
});
