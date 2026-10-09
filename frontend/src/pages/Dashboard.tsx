import AspectFrequency from "../components/charts/AspectFrequency";
import AspectSentimentBars from "../components/charts/AspectSentimentBars";
import SentimentDistribution from "../components/charts/SentimentDistribution";
import ModelPerformance from "../components/ModelPerformance";
import StateMessage from "../components/StateMessage";
import { useApi } from "../hooks/useApi";
import { describeError } from "../lib/errors";
import { percent } from "../lib/sentiment";
import { ApiError, getModelInfo, getStatistics } from "../services/api";

const TOP_ASPECTS = 10;

function share(part: number, whole: number): string {
  return whole > 0 ? percent(part / whole) : "n/a";
}

export default function Dashboard() {
  const statistics = useApi(() => getStatistics(TOP_ASPECTS));
  // Loaded separately: a missing evaluation report must not hide the charts.
  const modelInfo = useApi(() => getModelInfo());

  const stats = statistics.data;
  const statsError = statistics.failure ? describeError(statistics.failure) : null;
  const noReport = modelInfo.failure instanceof ApiError && modelInfo.failure.status === 404;
  const modelError = modelInfo.failure && !noReport ? describeError(modelInfo.failure) : null;

  const summary = stats && [
    { label: "Reviews analysed", value: String(stats.total_reviews) },
    { label: "Aspect mentions", value: String(stats.total_aspects) },
    {
      label: "Positive reviews",
      value: share(stats.overall_sentiment_distribution.positive, stats.total_reviews),
    },
    {
      label: "Positive aspect mentions",
      value: share(stats.aspect_sentiment_distribution.positive, stats.total_aspects),
    },
  ];

  return (
    <section className="space-y-8">
      <div className="space-y-4">
        <div>
          <h1 className="text-2xl font-semibold">Statistics Dashboard</h1>
          <p className="mt-1 text-sm text-slate-600">Aggregates over every review saved in the history.</p>
        </div>

        {statsError && (
          <StateMessage
            kind="error"
            title={statsError.title}
            message={statsError.message}
            onRetry={statsError.retryable ? statistics.reload : undefined}
          />
        )}
        {statistics.loading && !stats && <StateMessage kind="loading" message="Loading the statistics…" />}

        {!statsError && stats && summary && (
          <>
            <ul aria-label="Summary" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              {summary.map((item) => (
                <li key={item.label} className="rounded-lg border border-slate-200 bg-white p-4">
                  <span className="block text-xs text-slate-500">{item.label}</span>
                  <span className="mt-1 block text-2xl font-semibold tabular-nums">{item.value}</span>
                </li>
              ))}
            </ul>
            {stats.total_reviews === 0 ? (
              <StateMessage
                kind="empty"
                message="No reviews have been analysed yet. The charts appear once reviews are saved to the history."
              />
            ) : (
              <div className="grid gap-4 lg:grid-cols-2">
                <SentimentDistribution
                  counts={stats.overall_sentiment_distribution}
                  total={stats.total_reviews}
                />
                {stats.top_aspects.length > 0 ? (
                  <>
                    <AspectFrequency aspects={stats.top_aspects} />
                    <div className="lg:col-span-2">
                      <AspectSentimentBars aspects={stats.top_aspects} />
                    </div>
                  </>
                ) : (
                  <StateMessage kind="empty" message="None of the stored reviews mentions a product aspect." />
                )}
              </div>
            )}
          </>
        )}
      </div>

      <div className="space-y-3">
        <div>
          <h2 className="text-lg font-semibold">Model performance</h2>
          <p className="mt-1 text-sm text-slate-600">
            How accurate the deployed models are on reviews they were not trained on.
          </p>
        </div>
        {modelInfo.loading && !modelInfo.data && <StateMessage kind="loading" message="Loading the evaluation report…" />}
        {noReport && (
          <StateMessage
            kind="empty"
            message="No evaluation report yet. Run `python -m training.evaluate` in the backend folder to create it."
          />
        )}
        {modelError && (
          <StateMessage
            kind="error"
            title={modelError.title}
            message={modelError.message}
            onRetry={modelError.retryable ? modelInfo.reload : undefined}
          />
        )}
        {!modelInfo.failure && modelInfo.data && <ModelPerformance report={modelInfo.data.report} />}
      </div>
    </section>
  );
}
