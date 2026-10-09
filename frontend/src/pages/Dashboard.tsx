import JsonPreview from "../components/JsonPreview";
import { useApi } from "../hooks/useApi";
import { getStatistics } from "../services/api";

// TODO(frontend team): build the charts with Recharts (already installed):
//   - overall_sentiment_distribution  -> sentiment distribution chart
//   - top_aspects[].total             -> aspect frequency chart
//   - top_aspects[].positive/negative/neutral -> stacked bar per aspect
// getModelInfo() returns the models' test metrics for a "model performance" card.
export default function Dashboard() {
  const { data, error, loading } = useApi(() => getStatistics());

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Statistics Dashboard</h1>
      {loading && <p className="text-sm text-slate-600">Loading…</p>}
      {error && <p role="alert" className="text-sm text-red-800">{error}</p>}
      {data && <JsonPreview data={data} />}
    </section>
  );
}
