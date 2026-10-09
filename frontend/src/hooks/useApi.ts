import { useCallback, useEffect, useState } from "react";

interface ApiState<T> {
  data: T | null;
  error: string | null;
  /** What was thrown, for `describeError`; null when the last load succeeded. */
  failure: unknown;
  loading: boolean;
  reload: () => void;
}

/**
 * Loads data when the component mounts:
 *
 *   const { data, error, loading } = useApi(() => getStatistics());
 *
 * Pass `deps` to load again when an input (page number, filter, ...) changes.
 */
export function useApi<T>(load: () => Promise<T>, deps: unknown[] = []): ApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setFailure(null);
    load()
      .then((result) => !cancelled && setData(result))
      .catch((reason: unknown) => !cancelled && setFailure(reason))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [version, ...deps]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  const error = failure === null ? null : failure instanceof Error ? failure.message : String(failure);
  return { data, error, failure, loading, reload };
}
