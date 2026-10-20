// Cases found by the third independent review.
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { sourceForFile } from "../lib/csv";
import { analyzeReviews } from "../services/api";
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

beforeEach(() => {
  vi.mocked(analyzeReviews).mockReset().mockImplementation(async (reviews) => respond(reviews));
});

describe("how an uploaded file is read", () => {
  it("reads a .csv file as CSV and anything else line by line", () => {
    expect(sourceForFile({ name: "reviews.CSV", type: "" })).toBe("file");
    expect(sourceForFile({ name: "export", type: "text/csv" })).toBe("file");
    expect(sourceForFile({ name: "reviews.txt", type: "text/plain" })).toBe("paste");
  });

  it("keeps the commas of a .txt upload with one review per line", async () => {
    render(<Batch />);
    const file = new File(["Great food, slow service.\nNice screen, bad battery\n"], "reviews.txt", {
      type: "text/plain",
    });
    await userEvent.upload(screen.getByLabelText(/upload a csv file/i), file);
    expect(screen.getByRole("radio", { name: /one review per line/i })).toBeChecked();
    await userEvent.click(await screen.findByRole("button", { name: /analyze 2 reviews/i }));
    await waitFor(() =>
      expect(analyzeReviews).toHaveBeenCalledWith(["Great food, slow service.", "Nice screen, bad battery"], true),
    );
  });

  it("still reads an uploaded CSV as CSV after one row was removed in the box", async () => {
    render(<Batch />);
    const file = new File(['id,review\n1,"Great food, slow service."\n2,Bad row\n3,Nice keyboard\n'], "reviews.csv", {
      type: "text/csv",
    });
    await userEvent.upload(screen.getByLabelText(/upload a csv file/i), file);
    const box = screen.getByRole("textbox", { name: "Reviews" });
    await waitFor(() => expect(box).toHaveValue('id,review\n1,"Great food, slow service."\n2,Bad row\n3,Nice keyboard\n'));

    await userEvent.clear(box);
    await userEvent.click(box);
    await userEvent.paste('id,review\n1,"Great food, slow service."\n3,Nice keyboard\n');
    // Clearing the box switched to line mode; pasting the CSV back into an empty box is typed text.
    await userEvent.click(screen.getByRole("radio", { name: "CSV" }));
    await userEvent.type(box, "4,Quiet fan");

    expect(screen.getByRole("radio", { name: "CSV" })).toBeChecked();
    await userEvent.click(screen.getByRole("button", { name: /analyze 3 reviews/i }));
    await waitFor(() =>
      expect(analyzeReviews).toHaveBeenCalledWith(["Great food, slow service.", "Nice keyboard", "Quiet fan"], true),
    );
  });

  it("does not switch an edited CSV upload to line mode", async () => {
    render(<Batch />);
    const file = new File(["id,review\n1,Great food\n2,Bad rowx\n"], "reviews.csv", { type: "text/csv" });
    await userEvent.upload(screen.getByLabelText(/upload a csv file/i), file);
    const box = screen.getByRole("textbox", { name: "Reviews" });
    await waitFor(() => expect(box).toHaveValue("id,review\n1,Great food\n2,Bad rowx\n"));

    await userEvent.type(box, "{backspace}{backspace}"); // removes the newline and the typo
    expect(screen.getByRole("radio", { name: "CSV" })).toBeChecked();
    expect(screen.getByRole("button", { name: /analyze 2 reviews/i })).toBeInTheDocument();
  });

  it("lets the reader switch how the text is read", async () => {
    render(<Batch />);
    await userEvent.click(screen.getByRole("textbox", { name: "Reviews" }));
    await userEvent.paste("id,review\n1,Great food\n");
    expect(screen.getByRole("button", { name: /analyze 2 reviews/i })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "CSV" }));
    expect(screen.getByRole("button", { name: /analyze 1 review\b/i })).toBeInTheDocument();
  });
});
