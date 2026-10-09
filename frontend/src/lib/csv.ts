// Reading reviews from an uploaded CSV file and writing results back to CSV.

import type { AnalysisResponse } from "../types/api";

/** Same limit as the backend (schemas/analysis.py). */
export const MAX_REVIEW_CHARS = 5000;
/** Largest number of reviews taken from one file. */
export const MAX_BATCH_FILE_REVIEWS = 500;

const REVIEW_COLUMNS = ["review", "text"];

interface Row {
  fields: string[];
  /** 1-based line of the file on which the row starts. */
  line: number;
}

function parseRows(input: string): Row[] {
  const text = input.replace(/^﻿/, ""); // byte-order mark written by Excel
  const rows: Row[] = [];
  let fields: string[] = [];
  let field = "";
  let quoted = false;
  let line = 1;
  let rowLine = 1;
  let rowHasContent = false;

  const endRow = () => {
    fields.push(field);
    rows.push({ fields, line: rowLine });
    fields = [];
    field = "";
    rowHasContent = false;
  };

  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (quoted) {
      if (char === '"' && text[i + 1] === '"') {
        field += '"';
        i++;
      } else if (char === '"') {
        quoted = false;
      } else {
        if (char === "\n") line++;
        field += char;
      }
      continue;
    }
    if (char === '"' && field === "") {
      quoted = true;
      rowHasContent = true;
    } else if (char === ",") {
      fields.push(field);
      field = "";
      rowHasContent = true;
    } else if (char === "\n" || char === "\r") {
      if (char === "\r" && text[i + 1] === "\n") i++;
      endRow();
      line++;
      rowLine = line;
    } else {
      field += char;
      rowHasContent = true;
    }
  }
  if (rowHasContent || field !== "" || fields.length > 0) endRow(); // last line without a newline
  return rows;
}

/** A CSV text as rows of fields (RFC 4180 quoting). */
export function parseCsvRows(text: string): string[][] {
  return parseRows(text).map((row) => row.fields);
}

export interface ParsedReviews {
  reviews: string[];
  /** Rows that cannot be analysed, with the line they start on. */
  skipped: { line: number; reason: string }[];
  /** True when the file held more than MAX_BATCH_FILE_REVIEWS usable reviews. */
  truncated: boolean;
}

/**
 * Extracts the reviews from a CSV file or from pasted text.
 *
 * If the first row names a `review` or `text` column, that column is used and
 * the row is treated as a header. Otherwise every row's first column is a review.
 */
export function parseReviews(text: string): ParsedReviews {
  const rows = parseRows(text);
  const result: ParsedReviews = { reviews: [], skipped: [], truncated: false };
  if (rows.length === 0) return result;

  const header = rows[0].fields.map((name) => name.trim().toLowerCase());
  const named = header.findIndex((name) => REVIEW_COLUMNS.includes(name));
  const column = named >= 0 ? named : 0;
  const body = named >= 0 ? rows.slice(1) : rows;

  for (const row of body) {
    const review = (row.fields[column] ?? "").trim();
    if (!review) {
      result.skipped.push({ line: row.line, reason: "blank" });
    } else if (review.length > MAX_REVIEW_CHARS) {
      result.skipped.push({ line: row.line, reason: `longer than ${MAX_REVIEW_CHARS} characters` });
    } else if (result.reviews.length >= MAX_BATCH_FILE_REVIEWS) {
      result.truncated = true;
      break;
    } else {
      result.reviews.push(review);
    }
  }
  return result;
}

function escapeField(value: string): string {
  return /[",\r\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
}

/** One row per aspect (one row with empty aspect columns for a review without aspects). */
export function toCsv(items: AnalysisResponse[]): string {
  const rows: string[][] = [["review", "overall_sentiment", "aspect", "sentiment", "confidence"]];
  for (const item of items) {
    if (item.aspects.length === 0) {
      rows.push([item.review, item.overall_sentiment, "", "", ""]);
    }
    for (const aspect of item.aspects) {
      rows.push([
        item.review,
        item.overall_sentiment,
        aspect.aspect,
        aspect.sentiment,
        String(aspect.confidence),
      ]);
    }
  }
  return rows.map((row) => row.map(escapeField).join(",")).join("\r\n") + "\r\n";
}
