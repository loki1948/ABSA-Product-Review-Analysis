import { useState, type FormEvent } from "react";

import JsonPreview from "../components/JsonPreview";
import { analyzeReview } from "../services/api";
import type { AnalysisResponse } from "../types/api";

const EXAMPLE =
  "The screen is gorgeous and the keyboard feels great, but the battery life is terrible.";

// The request/response wiring below is complete. TODO(frontend team): replace
// <JsonPreview> with the real result UI (SentimentCard, AspectTable,
// SentimentChart, aspects highlighted in the review text). See frontend/README.md.
export default function Analyzer() {
  const [review, setReview] = useState(EXAMPLE);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      setResult(await analyzeReview(review));
    } catch (reason) {
      setResult(null);
      setError((reason as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Review Analyzer</h1>
      <form onSubmit={handleSubmit} className="space-y-3">
        <label htmlFor="review" className="block text-sm font-medium">
          Product review
        </label>
        <textarea
          id="review"
          value={review}
          onChange={(event) => setReview(event.target.value)}
          rows={5}
          maxLength={5000}
          placeholder="Enter your product review..."
          className="w-full rounded-md border border-slate-300 bg-white p-3 text-sm"
        />
        <button
          type="submit"
          disabled={loading || !review.trim()}
          className="rounded-md bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50"
        >
          {loading ? "Analyzing…" : "Analyze Review"}
        </button>
      </form>
      {error && (
        <p role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          {error}
        </p>
      )}
      {result && <JsonPreview data={result} />}
    </section>
  );
}
