import { useEffect, useState } from "react";

import { getHealth } from "../services/api";

type State = { tone: "checking" | "ok" | "warn" | "down"; text: string };

const dot: Record<State["tone"], string> = {
  checking: "bg-slate-400",
  ok: "bg-green-600",
  warn: "bg-amber-500",
  down: "bg-red-600",
};

/** Shows whether the frontend can reach the backend and whether the models are loaded. */
export default function ConnectionStatus() {
  const [state, setState] = useState<State>({ tone: "checking", text: "Checking backend…" });

  useEffect(() => {
    let cancelled = false;
    getHealth()
      .then((health) => {
        if (cancelled) return;
        setState(
          health.status === "ok"
            ? { tone: "ok", text: "Backend connected" }
            : { tone: "warn", text: health.detail ?? "Backend degraded" },
        );
      })
      .catch((error: Error) => {
        if (!cancelled) setState({ tone: "down", text: error.message });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <span className="flex items-center gap-2 text-xs text-slate-600" role="status">
      <span className={`h-2 w-2 shrink-0 rounded-full ${dot[state.tone]}`} />
      {state.text}
    </span>
  );
}
