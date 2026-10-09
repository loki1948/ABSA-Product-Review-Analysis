import { Fragment, useState } from "react";
import { useSearchParams } from "react-router-dom";

import AnalysisResult from "../components/AnalysisResult";
import ConfirmDialog from "../components/ConfirmDialog";
import Pagination from "../components/Pagination";
import SentimentBadge from "../components/SentimentBadge";
import StateMessage from "../components/StateMessage";
import { useApi } from "../hooks/useApi";
import { describeError, type ErrorDescription } from "../lib/errors";
import { SENTIMENTS, sentimentLabel } from "../lib/sentiment";
import { deleteReview, getReviews } from "../services/api";
import type { AnalysisResponse, Sentiment } from "../types/api";

const PAGE_SIZE = 10;

function formatDate(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "";
}

export default function History() {
  // The filter and the page live in the URL, so a reload or a shared link
  // shows the same view.
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get("page")) || 1);
  const filter = SENTIMENTS.find((s) => s === params.get("sentiment"));

  const { data, failure, loading, reload } = useApi(
    () => getReviews({ limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE, sentiment: filter }),
    [page, filter],
  );
  const [openId, setOpenId] = useState<number | null>(null);
  const [toDelete, setToDelete] = useState<AnalysisResponse | null>(null);
  const [deleteError, setDeleteError] = useState<ErrorDescription | null>(null);

  function show(next: { page?: number; sentiment?: Sentiment | undefined }) {
    const sentiment = "sentiment" in next ? next.sentiment : filter;
    const nextPage = next.page ?? 1;
    const query: Record<string, string> = {};
    if (sentiment) query.sentiment = sentiment;
    if (nextPage > 1) query.page = String(nextPage);
    setParams(query);
  }

  async function confirmDelete() {
    const target = toDelete;
    setToDelete(null);
    if (!target?.id) return;
    try {
      await deleteReview(target.id);
      setDeleteError(null);
      // Deleting the only review on a later page would leave an empty page.
      if (data && data.items.length === 1 && page > 1) show({ page: page - 1 });
      else reload();
    } catch (reason) {
      setDeleteError(describeError(reason));
    }
  }

  const error = failure ? describeError(failure) : null;

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Review History</h1>
          <p className="mt-1 text-sm text-slate-600">Every analysed review that was saved, newest first.</p>
        </div>
        <label className="text-sm">
          <span className="mr-2 text-slate-700">Overall sentiment</span>
          <select
            value={filter ?? ""}
            onChange={(event) => show({ sentiment: (event.target.value || undefined) as Sentiment | undefined })}
            className="rounded-md border border-slate-300 bg-white px-2 py-1"
          >
            <option value="">All</option>
            {SENTIMENTS.map((sentiment) => (
              <option key={sentiment} value={sentiment}>
                {sentimentLabel(sentiment)}
              </option>
            ))}
          </select>
        </label>
      </div>

      {deleteError && <StateMessage kind="error" title={deleteError.title} message={deleteError.message} />}
      {error && (
        <StateMessage
          kind="error"
          title={error.title}
          message={error.message}
          onRetry={error.retryable ? reload : undefined}
        />
      )}
      {loading && !data && <StateMessage kind="loading" message="Loading the review history…" />}

      {!error && data && data.items.length === 0 && (
        <StateMessage
          kind="empty"
          message={
            filter
              ? `No ${filter} reviews in the history.`
              : "No reviews have been analysed yet. Analyse one on the Analyzer page and it will appear here."
          }
        />
      )}

      {!error && data && data.items.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white" aria-busy={loading}>
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-600">
                <tr>
                  <th scope="col" className="px-3 py-2">Date</th>
                  <th scope="col" className="px-3 py-2">Review</th>
                  <th scope="col" className="px-3 py-2">Overall</th>
                  <th scope="col" className="px-3 py-2">Aspects</th>
                  <th scope="col" className="px-3 py-2">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <Fragment key={item.id}>
                    <tr className="border-t border-slate-100 align-top">
                      <td className="whitespace-nowrap px-3 py-2 text-slate-600">{formatDate(item.created_at)}</td>
                      <td className="max-w-md px-3 py-2">
                        <span className="line-clamp-2">{item.review}</span>
                      </td>
                      <td className="px-3 py-2">
                        <SentimentBadge sentiment={item.overall_sentiment} />
                      </td>
                      <td className="whitespace-nowrap px-3 py-2 text-slate-600">
                        {item.aspects.length} {item.aspects.length === 1 ? "aspect" : "aspects"}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2 text-right">
                        <button
                          type="button"
                          aria-label={`View analysis of review ${item.id}`}
                          aria-expanded={openId === item.id}
                          onClick={() => setOpenId(openId === item.id ? null : item.id)}
                          className="mr-3 text-blue-700 hover:underline"
                        >
                          {openId === item.id ? "Hide" : "View"}
                        </button>
                        <button
                          type="button"
                          aria-label={`Delete review ${item.id}`}
                          onClick={() => setToDelete(item)}
                          className="text-red-700 hover:underline"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                    {openId === item.id && (
                      <tr className="border-t border-slate-100 bg-slate-50">
                        <td colSpan={5} className="p-3">
                          <AnalysisResult result={item} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onChange={(next) => show({ page: next })} />
        </>
      )}

      {toDelete && (
        <ConfirmDialog
          title="Delete this review?"
          message="The review and its aspects are removed from the history and the statistics. This cannot be undone."
          confirmLabel="Delete"
          onConfirm={confirmDelete}
          onCancel={() => setToDelete(null)}
        />
      )}
    </section>
  );
}
