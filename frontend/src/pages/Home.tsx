import { Link } from "react-router-dom";

import AnalysisResult from "../components/AnalysisResult";
import type { AnalysisResponse, AspectResult, Sentiment } from "../types/api";

const EXAMPLE_REVIEW =
  "The screen is gorgeous and the keyboard feels great, but the battery life is terrible.";

function exampleAspect(term: string, sentiment: Sentiment, confidence: number, context: string): AspectResult {
  const start = EXAMPLE_REVIEW.indexOf(term);
  return { aspect: term, sentiment, confidence, context, start, end: start + term.length };
}

// A fixed illustration, not model output: it shows the idea without needing
// the backend. Measured accuracy is on the Dashboard.
const EXAMPLE: AnalysisResponse = {
  id: null,
  review: EXAMPLE_REVIEW,
  overall_sentiment: "neutral",
  overall_confidence: 0.6,
  aspects: [
    exampleAspect("screen", "positive", 0.97, "The screen is gorgeous"),
    exampleAspect("keyboard", "positive", 0.95, "the keyboard feels great"),
    exampleAspect("battery life", "negative", 0.96, "the battery life is terrible"),
  ],
  created_at: null,
};

const STEPS = [
  {
    title: "1. Find the aspects",
    text: "A BERT model reads the review word by word and marks the words that name a part or feature of the product. No list of aspects is built in: the model learnt what an aspect looks like from annotated reviews.",
  },
  {
    title: "2. Judge each aspect",
    text: "A second BERT model receives the sentence together with one aspect and decides whether the review is positive, negative or neutral about that aspect.",
  },
  {
    title: "3. Compare with one label",
    text: "A third model gives the whole review a single label, as a traditional system would, so the two views can be seen side by side.",
  },
];

export default function Home() {
  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <h1 className="max-w-3xl text-3xl font-semibold leading-tight">
          Aspect-Based Sentiment Analysis for Automated Product Review Analysis
        </h1>
        <p className="max-w-2xl text-slate-700">
          Traditional sentiment analysis gives a review one label. Real reviews are rarely that
          simple: the same sentence can praise the screen and complain about the battery.
        </p>
        <p className="max-w-2xl text-slate-700">
          This system finds the individual product aspects a review talks about and the sentiment
          towards each one, so a seller can see what customers like and what needs fixing.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link
            to="/analyze"
            className="rounded-md bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800"
          >
            Analyze a review
          </Link>
          <Link
            to="/dashboard"
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:border-blue-600"
          >
            See the statistics
          </Link>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">One review, two views</h2>
        <p className="max-w-2xl text-sm text-slate-600">
          An illustration of what the system returns. The single label hides what the aspect-based
          view makes visible.
        </p>
        <AnalysisResult result={EXAMPLE} />
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">How it works</h2>
        <ol className="grid gap-4 md:grid-cols-3">
          {STEPS.map((step) => (
            <li key={step.title} className="rounded-lg border border-slate-200 bg-white p-4">
              <h3 className="text-sm font-semibold">{step.title}</h3>
              <p className="mt-2 text-sm text-slate-600">{step.text}</p>
            </li>
          ))}
        </ol>
        <p className="max-w-2xl text-sm text-slate-600">
          The models are trained on the SemEval-2014 laptop and restaurant reviews. Many reviews can
          be analysed at once on the{" "}
          <Link to="/batch" className="text-blue-700 hover:underline">
            Batch page
          </Link>
          .
        </p>
      </section>
    </div>
  );
}
