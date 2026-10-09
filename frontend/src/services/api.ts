// The single connection point between the frontend and the FastAPI backend.
// Components never call fetch() themselves; they call the functions below.

import type {
  AnalysisResponse,
  BatchAnalysisResponse,
  HealthResponse,
  ModelInfoResponse,
  ReviewListResponse,
  Sentiment,
  StatisticsResponse,
} from "../types/api";

const BASE_URL = `${import.meta.env.VITE_API_BASE_URL ?? ""}/api`;

/** Thrown for every failed request; `message` is safe to show to the user. */
export class ApiError extends Error {
  constructor(
    message: string,
    /** HTTP status, or 0 when the backend could not be reached at all. */
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function errorMessage(status: number, body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  // FastAPI validation errors (422): detail is a list of { msg, loc, ... }.
  if (Array.isArray(detail)) {
    return detail.map((item: { msg?: string }) => item.msg ?? "Invalid input").join("; ");
  }
  return `Request failed (HTTP ${status}).`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError("Cannot reach the backend. Is it running on port 8000?", 0);
  }
  if (response.status === 204) return undefined as T;
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(errorMessage(response.status, body), response.status);
  return body as T;
}

function query(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

/** POST /api/analyze - run the ABSA pipeline on one review. */
export function analyzeReview(review: string, save = true): Promise<AnalysisResponse> {
  return request("/analyze", { method: "POST", body: JSON.stringify({ review, save }) });
}

/** POST /api/analyze/batch - analyse up to 50 reviews in one request. */
export function analyzeReviews(reviews: string[], save = true): Promise<BatchAnalysisResponse> {
  return request("/analyze/batch", { method: "POST", body: JSON.stringify({ reviews, save }) });
}

/** GET /api/reviews - review history, newest first. */
export function getReviews(
  options: { limit?: number; offset?: number; sentiment?: Sentiment } = {},
): Promise<ReviewListResponse> {
  return request(`/reviews${query(options)}`);
}

/** GET /api/reviews/{id} */
export function getReview(id: number): Promise<AnalysisResponse> {
  return request(`/reviews/${id}`);
}

/** DELETE /api/reviews/{id} */
export function deleteReview(id: number): Promise<void> {
  return request(`/reviews/${id}`, { method: "DELETE" });
}

/** GET /api/statistics - aggregates for the dashboard charts. */
export function getStatistics(topN?: number): Promise<StatisticsResponse> {
  return request(`/statistics${query({ top_n: topN })}`);
}

/** GET /api/health */
export function getHealth(): Promise<HealthResponse> {
  return request("/health");
}

/** GET /api/model-info - test-set metrics of the deployed models. */
export function getModelInfo(): Promise<ModelInfoResponse> {
  return request("/model-info");
}
