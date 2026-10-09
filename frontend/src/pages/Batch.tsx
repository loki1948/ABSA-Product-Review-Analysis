import { useMemo, useRef, useState, type ChangeEvent } from "react";

import SentimentBadge from "../components/SentimentBadge";
import StateMessage from "../components/StateMessage";
import { MAX_BATCH_FILE_REVIEWS, parseReviews, toCsv } from "../lib/csv";
import { describeError, type ErrorDescription } from "../lib/errors";
import { badgeClass, sentimentLabel } from "../lib/sentiment";
import { analyzeReviews } from "../services/api";
import type { AnalysisResponse } from "../types/api";

/** Reviews per request. Small chunks give real progress and short requests. */
const CHUNK_SIZE = 10;

type Status = "idle" | "running" | "finished" | "stopped";

function download(filename: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export default function Batch() {
  const [text, setText] = useState("");
  const [save, setSave] = useState(true);
  const [status, setStatus] = useState<Status>("idle");
  const [results, setResults] = useState<AnalysisResponse[]>([]);
  const [target, setTarget] = useState(0);
  const [error, setError] = useState<ErrorDescription | null>(null);
  const cancelled = useRef(false);

  const parsed = useMemo(() => parseReviews(text), [text]);
  const count = parsed.reviews.length;
  const running = status === "running";

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) setText(await file.text());
    event.target.value = ""; // choosing the same file again must fire again
  }

  async function run() {
    const reviews = parsed.reviews;
    cancelled.current = false;
    setResults([]);
    setTarget(reviews.length);
    setError(null);
    setStatus("running");

    const collected: AnalysisResponse[] = [];
    for (let start = 0; start < reviews.length; start += CHUNK_SIZE) {
      if (cancelled.current) break;
      try {
        const response = await analyzeReviews(reviews.slice(start, start + CHUNK_SIZE), save);
        collected.push(...response.items);
        setResults([...collected]);
      } catch (reason) {
        // Keep what has been analysed so far: it can still be read and exported.
        setError(describeError(reason));
        break;
      }
    }
    setStatus(collected.length === reviews.length ? "finished" : "stopped");
  }

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Batch Analysis</h1>
        <p className="mt-1 text-sm text-slate-600">
          Analyse many reviews at once: upload a CSV file or paste one review per line.
        </p>
      </div>

      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <label
            htmlFor="batch-file"
            className="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-1.5 hover:border-blue-600"
          >
            Upload a CSV file
          </label>
          <input
            id="batch-file"
            type="file"
            accept=".csv,text/csv,text/plain"
            onChange={handleFile}
            disabled={running}
            className="sr-only"
          />
          <span className="text-xs text-slate-500">
            Uses the column named <code>review</code> or <code>text</code>, or the first column. At
            most {MAX_BATCH_FILE_REVIEWS} reviews.
          </span>
        </div>
        <label htmlFor="batch-text" className="block text-sm font-medium">
          Reviews, one review per line
        </label>
        <textarea
          id="batch-text"
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={8}
          disabled={running}
          placeholder={"The screen is gorgeous but the battery life is terrible.\nGreat food, slow service."}
          className="w-full rounded-md border border-slate-300 bg-white p-3 font-mono text-xs focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-200"
        />

        {parsed.skipped.length > 0 && (
          <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            <p className="font-medium">
              {parsed.skipped.length} {parsed.skipped.length === 1 ? "row" : "rows"} skipped
            </p>
            <ul className="mt-1 list-inside list-disc text-xs">
              {parsed.skipped.slice(0, 10).map((row) => (
                <li key={row.line}>
                  line {row.line}: {row.reason}
                </li>
              ))}
              {parsed.skipped.length > 10 && <li>and {parsed.skipped.length - 10} more</li>}
            </ul>
          </div>
        )}
        {parsed.truncated && (
          <p className="text-sm text-amber-800">
            Only the first {MAX_BATCH_FILE_REVIEWS} reviews will be analysed.
          </p>
        )}

        <div className="flex flex-wrap items-center gap-4">
          <button
            type="button"
            onClick={run}
            disabled={running || count === 0}
            className="rounded-md bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Analyze {count} {count === 1 ? "review" : "reviews"}
          </button>
          {running && (
            <button
              type="button"
              onClick={() => (cancelled.current = true)}
              className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:border-red-600 hover:text-red-700"
            >
              Cancel
            </button>
          )}
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={save}
              onChange={(event) => setSave(event.target.checked)}
              disabled={running}
              className="h-4 w-4"
            />
            Save to history
          </label>
        </div>
      </div>

      {status !== "idle" && (
        <div className="space-y-2" role="status">
          <div
            className="h-2 overflow-hidden rounded-full bg-slate-200"
            role="progressbar"
            aria-label="Reviews analysed"
            aria-valuemin={0}
            aria-valuemax={target}
            aria-valuenow={results.length}
          >
            <div
              className="h-full bg-blue-700 transition-all"
              style={{ width: `${target ? (results.length / target) * 100 : 0}%` }}
            />
          </div>
          <p className="text-sm text-slate-700">
            {status === "stopped"
              ? `Stopped after ${results.length} of ${target} reviews.`
              : `Analysed ${results.length} of ${target} reviews${running ? "…" : "."}`}
          </p>
        </div>
      )}

      {error && <StateMessage kind="error" title={error.title} message={error.message} />}

      {results.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Results</h2>
            <button
              type="button"
              onClick={() => download("absa-results.csv", toCsv(results))}
              className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm hover:border-blue-600"
            >
              Download results (CSV)
            </button>
          </div>
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-600">
                <tr>
                  <th scope="col" className="px-3 py-2">Review</th>
                  <th scope="col" className="px-3 py-2">Overall</th>
                  <th scope="col" className="px-3 py-2">Aspects</th>
                </tr>
              </thead>
              <tbody>
                {results.map((item, index) => (
                  <tr key={index} className="border-t border-slate-100 align-top">
                    <td className="max-w-md px-3 py-2">{item.review}</td>
                    <td className="px-3 py-2">
                      <SentimentBadge sentiment={item.overall_sentiment} />
                    </td>
                    <td className="px-3 py-2">
                      {item.aspects.length === 0 ? (
                        <span className="text-slate-500">none found</span>
                      ) : (
                        <ul className="flex flex-wrap gap-1.5">
                          {item.aspects.map((aspect) => (
                            <li
                              key={`${aspect.start}-${aspect.end}`}
                              title={sentimentLabel(aspect.sentiment)}
                              className={`rounded-full border px-2 py-0.5 text-xs ${badgeClass(aspect.sentiment)}`}
                            >
                              {aspect.aspect}
                              <span className="sr-only">: {sentimentLabel(aspect.sentiment)}</span>
                              <span aria-hidden="true">
                                {aspect.sentiment === "positive" ? " +" : aspect.sentiment === "negative" ? " −" : " ○"}
                              </span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
