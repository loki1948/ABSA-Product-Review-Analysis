import { Bar, BarChart, CartesianGrid, LabelList, Tooltip, XAxis, YAxis } from "recharts";

import type { AspectStatistics } from "../../types/api";
import ChartFigure from "./ChartFigure";

/** The aspects mentioned most often across all stored reviews. */
export default function AspectFrequency({ aspects }: { aspects: AspectStatistics[] }) {
  const words = aspects.map((a) => `${a.aspect} (${a.total})`).join(", ");
  return (
    <ChartFigure
      title="Most frequent aspects"
      description={`Most frequent aspects: ${words}`}
      height={Math.max(200, aspects.length * 34 + 40)}
    >
      <BarChart data={aspects} layout="vertical" margin={{ top: 0, right: 28, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" allowDecimals={false} />
        <YAxis type="category" dataKey="aspect" width={110} />
        <Tooltip />
        <Bar dataKey="total" name="Mentions" fill="#1d4ed8" isAnimationActive={false}>
          <LabelList dataKey="total" position="right" />
        </Bar>
      </BarChart>
    </ChartFigure>
  );
}
