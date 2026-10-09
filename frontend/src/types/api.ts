// Types of the backend's JSON. They mirror backend/app/schemas/analysis.py
// field for field - when one changes, change the other.

export type Sentiment = "positive" | "negative" | "neutral";

export interface AspectResult {
  /** Aspect term exactly as written in the review. */
  aspect: string;
  sentiment: Sentiment;
  /** Probability of the predicted sentiment, 0..1. */
  confidence: number;
  /** Clause of the review that talks about the aspect. */
  context: string;
  /** Character offsets of the aspect in `AnalysisResponse.review`. */
  start: number;
  end: number;
}

export interface AnalysisResponse {
  /** History id; null when analysed with save=false. */
  id: number | null;
  review: string;
  overall_sentiment: Sentiment;
  overall_confidence: number;
  aspects: AspectResult[];
  /** ISO-8601 UTC timestamp; null when not saved. */
  created_at: string | null;
}

export interface BatchAnalysisResponse {
  total: number;
  /** One result per review, in request order. */
  items: AnalysisResponse[];
}

export interface ReviewListResponse {
  total: number;
  limit: number;
  offset: number;
  items: AnalysisResponse[];
}

export interface SentimentCounts {
  positive: number;
  negative: number;
  neutral: number;
}

export interface AspectStatistics extends SentimentCounts {
  /** Normalised aspect (lowercase, singular). */
  aspect: string;
  total: number;
}

export interface StatisticsResponse {
  total_reviews: number;
  total_aspects: number;
  overall_sentiment_distribution: SentimentCounts;
  aspect_sentiment_distribution: SentimentCounts;
  top_aspects: AspectStatistics[];
}

export interface HealthResponse {
  status: "ok" | "degraded";
  models_loaded: boolean;
  database: boolean;
  detail: string | null;
}

export interface ModelInfoResponse {
  /** Contents of models/evaluation_report.json (see docs/API.md). */
  report: Record<string, unknown>;
}
