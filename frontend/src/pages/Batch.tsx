import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";

import SentimentBadge from "../components/SentimentBadge";
import StateMessage from "../components/StateMessage";
import { MAX_BATCH_FILE_REVIEWS, parseReviews, sourceForFile, toCsv, type ReviewSource } from "../lib/csv";
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
  // A .csv upload is read as CSV; typed text and .txt files are one review per line.
  // Editing an uploaded file keeps its mode; the radio buttons show and change it.
  const [source, setSource] = useState<ReviewSource>("paste");
  const [save, setSave] = useState(true);
  const [status, setStatus] = useState<Status>("idle");
  const [results, setResults] = useState<AnalysisResponse[]>([]);
  const [target, setTarget] = useState(0);
  const [error, setError] = useState<ErrorDescription | null>(null);
  const [stopping, setStopping] = useState(false);
  const cancelled = useRef(false);
  /** True when Cancel was pressed (as opposed to the page being left). */
  const stoppedByUser = useRef(false);
  /** The reviews of the last run, to tell "continue" from "start again". */
  const lastRun = useRef<string[]>([]);

  // Leaving the page must stop the run: otherwise it keeps posting (and saving) chunks.
  useEffect(
    () => () => {
      cancelled.current = true;
    },
    [],
  );

  const parsed = useMemo(() => parseReviews(text, source), [text, source]);
  const count = parsed.reviews.length;
  const running = status === "running";
  // After a stop, the same list can be continued where it stopped, so reviews
  // that were already analysed (and saved) are not sent a second time.
  const sameList =
    lastRun.current.length === count && lastRun.current.every((review, i) => review === parsed.reviews[i]);
  const remaining = status === "stopped" && sameList ? count - results.length : 0;

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) {
      setText(await file.text());
      setSource(sourceForFile(file));
    }
    event.target.value = ""; // choosing the same file again must fire again
  }

  async function run() {
    const reviews = parsed.reviews;
    const collected: AnalysisResponse[] = remaining > 0 ? [...results] : [];
    lastRun.current = reviews;
    cancelled.current = false;
    stoppedByUser.current = false;
    setStopping(false);
    setResults(collected);
    setTarget(reviews.length);
    setError(null);
    setStatus("running");

    for (let start = collected.length; start < reviews.length; start += CHUNK_SIZE) {
      if (cancelled.current) break;
      try {
        const response = await analyzeReviews(reviews.slice(start, start + CHUNK_SIZE), save);
        collected.push(...response.items);
        if (cancelled.current && !stoppedByUser.current) return; // the page was left
        setResults([...collected]);
      } catch (reason) {
        // Keep what has been analysed so far: it can still be read and exported.
        setError(describeError(reason));
        break;
      }
    }
    setStopping(false);
    setStatus(collected.length === reviews.length ? "finished" : "stopped");
  }

  function cancel() {
    stoppedByUser.current = true;
    cancelled.current = true;
    setStopping(true);
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
            A .csv file is read as CSV: the column named <code>review</code> or <code>text</code>,
            or the first column. A .txt file is one review per line. At most{" "}
            {MAX_BATCH_FILE_REVIEWS} reviews.
          </span>
        </div>
        <fieldset className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm" disabled={running}>
          <legend className="sr-only">How the text is read</legend>
          <span className="text-slate-600">Read the text as:</span>
          <label className="flex min-h-11 items-center gap-1.5">
            <input
              type="radio"
              name="batch-source"
              checked={source === "paste"}
              onChange={() => setSource("paste")}
            />
            one review per line
          </label>
          <label className="flex min-h-11 items-center gap-1.5">
            <input
              type="radio"
              name="batch-source"
              checked={source === "file"}
              onChange={() => setSource("file")}
            />
            CSV
          </label>
        </fieldset>
        <label htmlFor="batch-text" className="block text-sm font-medium">
          Reviews
        </label>
        <textarea
          id="batch-text"
          value={text}
          onChange={(event) => {
            const value = event.target.value;
            // Text typed into an empty box is one review per line; editing an
            // uploaded CSV must not silently change how the rest is read.
            if (value.trim() === "" || text.trim() === "") setSource("paste");
            setText(value);
          }}
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
            {remaining > 0
              ? `Continue with the remaining ${remaining}`
              : `Analyze ${count} ${count === 1 ? "review" : "reviews"}`}
          </button>
          {running && (
            <button
              type="button"
              onClick={cancel}
              disabled={stopping}
              className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:border-red-600 hover:text-red-700 disabled:opacity-60"
            >
              {stopping ? "Stopping…" : "Cancel"}
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
          <div className="relative overflow-x-auto rounded-lg border border-slate-200 bg-white">
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
