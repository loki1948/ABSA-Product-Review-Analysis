// How a sentiment is named and coloured, in one place. Colour is never the
// only signal: every badge and chart series also carries the word.

import type { Sentiment } from "../types/api";

/** Display order used by tables, legends and stacked charts. */
export const SENTIMENTS: Sentiment[] = ["positive", "neutral", "negative"];

const LABELS: Record<Sentiment, string> = {
  positive: "Positive",
  neutral: "Neutral",
  negative: "Negative",
};

const BADGE: Record<Sentiment, string> = {
  positive: "bg-green-100 text-green-900 border-green-300",
  neutral: "bg-slate-100 text-slate-800 border-slate-300",
  negative: "bg-red-100 text-red-900 border-red-300",
};

const HIGHLIGHT: Record<Sentiment, string> = {
  positive: "bg-green-100 text-green-950 decoration-green-600",
  neutral: "bg-slate-200 text-slate-900 decoration-slate-500",
  negative: "bg-red-100 text-red-950 decoration-red-600",
};

const CHART: Record<Sentiment, string> = {
  positive: "#15803d",
  neutral: "#64748b",
  negative: "#b91c1c",
};

export function sentimentLabel(sentiment: Sentiment): string {
  return LABELS[sentiment];
}

/** Tailwind classes for a small bordered pill. */
export function badgeClass(sentiment: Sentiment): string {
  return BADGE[sentiment];
}

/** Tailwind classes for an aspect marked inside the review text. */
export function highlightClass(sentiment: Sentiment): string {
  return HIGHLIGHT[sentiment];
}

/** Hex colour for Recharts series. */
export function chartColor(sentiment: Sentiment): string {
  return CHART[sentiment];
}

/** 0.954 -> "95%". Only an exact 1 is shown as 100%: 0.997 is "99%", not certainty. */
export function percent(value: number): string {
  const rounded = Math.round(value * 100);
  return `${value < 1 ? Math.min(rounded, 99) : rounded}%`;
}
