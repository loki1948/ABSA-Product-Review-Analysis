interface Props {
  kind: "loading" | "empty" | "error";
  title?: string;
  message: string;
  /** Shown as a "Try again" button. */
  onRetry?: () => void;
}

const styles: Record<Props["kind"], string> = {
  loading: "border-slate-200 bg-white text-slate-600",
  empty: "border-dashed border-slate-300 bg-white text-slate-600",
  error: "border-red-200 bg-red-50 text-red-900",
};

/** The box every page uses while loading, when there is nothing to show, or on failure. */
export default function StateMessage({ kind, title, message, onRetry }: Props) {
  return (
    <div
      role={kind === "error" ? "alert" : "status"}
      className={`rounded-lg border p-4 text-sm ${styles[kind]}`}
    >
      {title && <p className="font-semibold">{title}</p>}
      <p className={`whitespace-pre-line ${title ? "mt-1" : ""}`}>{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-md border border-current px-3 py-1 text-xs font-medium hover:bg-white/60"
        >
          Try again
        </button>
      )}
    </div>
  );
}
