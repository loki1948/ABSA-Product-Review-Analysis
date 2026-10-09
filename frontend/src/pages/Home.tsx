import { Link } from "react-router-dom";

// TODO(frontend team): design the landing page - project explanation, a
// "traditional vs. aspect-based" comparison, an example review. See frontend/README.md.
export default function Home() {
  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">
        Aspect-Based Sentiment Analysis for Automated Product Review Analysis
      </h1>
      <p className="max-w-2xl text-slate-600">
        Traditional sentiment analysis gives a review one label. This system finds the individual
        product aspects a review talks about and the sentiment towards each of them.
      </p>
      <Link
        to="/analyze"
        className="inline-block rounded-md bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800"
      >
        Analyze a review
      </Link>
    </section>
  );
}
