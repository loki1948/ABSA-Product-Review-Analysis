import { useEffect, useState } from "react";

import AnalysisResult from "../components/AnalysisResult";
import ReviewInput from "../components/ReviewInput";
import StateMessage from "../components/StateMessage";
import { describeError, type ErrorDescription } from "../lib/errors";
import { analyzeReview, getHealth } from "../services/api";
import type { AnalysisResponse } from "../types/api";

export default function Analyzer() {
  const [review, setReview] = useState("");
  const [save, setSave] = useState(true);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<ErrorDescription | null>(null);
  const [busy, setBusy] = useState(false);
  const [modelsMissing, setModelsMissing] = useState<string | undefined>();

  // Ask once whether the models are loaded, so the form can say why it is
  // disabled instead of failing on submit. If the backend is unreachable the
  // form stays enabled and the submit error explains it.
  useEffect(() => {
    let cancelled = false;
    getHealth()
      .then((health) => {
        if (!cancelled && !health.models_loaded) {
          setModelsMissing(health.detail ?? "The models are not loaded.");
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      setResult(await analyzeReview(review, save));
    } catch (reason) {
      setResult(null);
      setError(describeError(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Review Analyzer</h1>
        <p className="mt-1 text-sm text-slate-600">
          Find the product aspects a review mentions and the sentiment towards each one.
        </p>
      </div>
      <ReviewInput
        value={review}
        onChange={setReview}
        save={save}
        onSaveChange={setSave}
        onSubmit={submit}
        busy={busy}
        disabledReason={modelsMissing}
      />
      {error && (
        <StateMessage
          kind="error"
          title={error.title}
          message={error.message}
          onRetry={error.retryable ? submit : undefined}
        />
      )}
      {result && (
        <div className={busy ? "opacity-50" : undefined} aria-busy={busy}>
          <AnalysisResult result={result} />
        </div>
      )}
    </section>
  );
}
