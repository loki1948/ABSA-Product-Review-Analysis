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
  // Empty lines at the end of a file are not rows.
  while (rows.length > 0 && rows[rows.length - 1].fields.every((value) => value === "")) rows.pop();
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

/** One review per line; a line that is a single quoted CSV field is unwrapped. */
function lineRows(input: string): Row[] {
  const lines = input.replace(/^\uFEFF/, "").split(/\r\n|\n|\r/);
  while (lines.length > 0 && lines[lines.length - 1].trim() === "") lines.pop();
  return lines.map((raw, index) => {
    const line = raw.trim();
    // Exactly one quoted field: no quote inside except doubled ones. A sentence
    // such as "Wow" and "amazing" keeps its quotes.
    if (line.length > 1 && line.startsWith('"') && line.endsWith('"')) {
      const inner = line.slice(1, -1);
      if (!inner.replace(/""/g, "").includes('"')) {
        return { fields: [inner.replace(/""/g, '"')], line: index + 1 };
      }
    }
    return { fields: [line], line: index + 1 };
  });
}

/** Where the text came from decides how it is read. */
export type ReviewSource = "file" | "paste";

/**
 * Extracts the reviews from an uploaded CSV file or from typed text.
 *
 * - `file`: read as CSV. The column named `review` or `text` is used; without
 *   such a header, the first column of every row.
 * - `paste`: every line is one review, commas and all. People type sentences,
 *   and "Great food, slow service." must not be cut at the comma, nor a first
 *   line that happens to start with "Text" be taken for a header.
 */
export function parseReviews(text: string, source: ReviewSource = "file"): ParsedReviews {
  const result: ParsedReviews = { reviews: [], skipped: [], truncated: false };
  let column = 0;
  let body: Row[];
  if (source === "paste") {
    body = lineRows(text);
  } else {
    const rows = parseRows(text);
    const header = (rows[0]?.fields ?? []).map((name) => name.trim().toLowerCase());
    const named = header.findIndex((name) => REVIEW_COLUMNS.includes(name));
    column = named >= 0 ? named : 0;
    body = named >= 0 ? rows.slice(1) : rows;
  }

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

/**
 * Spreadsheets run a cell that starts with one of these characters as a
 * formula. Review text is not ours, so such a cell gets a leading apostrophe:
 * the cell is then plain text and nothing is executed. The apostrophe stays
 * visible in the opened file; that is the price of the protection.
 */
const FORMULA_START = /^[=+\-@\t\r]/;

function escapeField(value: string, untrusted = true): string {
  const safe = untrusted && FORMULA_START.test(value) ? `'${value}` : value;
  return /[",\r\n]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe;
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
  // Columns 0 and 2 hold review and aspect text; the others are our own labels and numbers.
  return (
    rows.map((row) => row.map((cell, column) => escapeField(cell, column === 0 || column === 2)).join(",")).join("\r\n") +
    "\r\n"
  );
}
