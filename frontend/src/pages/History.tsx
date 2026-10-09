import JsonPreview from "../components/JsonPreview";
import { useApi } from "../hooks/useApi";
import { getReviews } from "../services/api";

// TODO(frontend team): render the history as a list/table with pagination
// (limit/offset), a sentiment filter and a delete button (deleteReview).
export default function History() {
  const { data, error, loading } = useApi(() => getReviews({ limit: 20 }));

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Review History</h1>
      {loading && <p className="text-sm text-slate-600">Loading…</p>}
      {error && <p role="alert" className="text-sm text-red-800">{error}</p>}
      {data && <JsonPreview data={data} />}
    </section>
  );
}
