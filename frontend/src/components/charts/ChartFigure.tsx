import type { ReactElement } from "react";
import { ResponsiveContainer } from "recharts";

interface Props {
  title: string;
  /** The chart's data in words, for screen readers and for tests. */
  description: string;
  height?: number;
  children: ReactElement;
}

/** A titled card around one Recharts chart. */
export default function ChartFigure({ title, description, height = 260, children }: Props) {
  return (
    <figure aria-label={description} className="rounded-lg border border-slate-200 bg-white p-4">
      <figcaption className="mb-3 text-sm font-semibold text-slate-700">{title}</figcaption>
      <div style={{ height }} aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          {children}
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
