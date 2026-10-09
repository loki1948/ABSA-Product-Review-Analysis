import type { AspectResult } from "../types/api";

/** A stretch of the review: plain text, or one aspect. */
export interface Segment {
  text: string;
  aspect: AspectResult | null;
}

/**
 * Cuts a review into plain and aspect segments using the aspects' character
 * offsets. Joining every segment's text gives the review back.
 *
 * Offsets that cannot be right (outside the text, empty, or overlapping an
 * earlier aspect) are skipped, so a bad record shows as plain text instead of
 * breaking the page.
 */
export function segments(review: string, aspects: AspectResult[]): Segment[] {
  const usable = aspects
    .filter((a) => a.start >= 0 && a.end <= review.length && a.start < a.end)
    .sort((a, b) => a.start - b.start);

  const result: Segment[] = [];
  let position = 0;
  for (const aspect of usable) {
    if (aspect.start < position) continue; // overlaps the previous aspect
    if (aspect.start > position) {
      result.push({ text: review.slice(position, aspect.start), aspect: null });
    }
    result.push({ text: review.slice(aspect.start, aspect.end), aspect });
    position = aspect.end;
  }
  if (position < review.length || result.length === 0) {
    result.push({ text: review.slice(position), aspect: null });
  }
  return result;
}
