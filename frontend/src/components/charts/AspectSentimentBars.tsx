import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from "recharts";

import { chartColor, SENTIMENTS, sentimentLabel } from "../../lib/sentiment";
import type { AspectStatistics } from "../../types/api";
import ChartFigure from "./ChartFigure";

/** For each frequent aspect, how its mentions divide into the three sentiments. */
export default function AspectSentimentBars({ aspects }: { aspects: AspectStatistics[] }) {
  const words = aspects
    .map((a) => `${a.aspect}: ${SENTIMENTS.map((s) => `${a[s]} ${s}`).join(", ")}`)
    .join("; ");
  return (
    <ChartFigure
      title="Sentiment per aspect"
      description={`Sentiment per aspect. ${words}`}
      height={Math.max(220, aspects.length * 34 + 70)}
    >
      <BarChart data={aspects} layout="vertical" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" allowDecimals={false} />
        <YAxis type="category" dataKey="aspect" width={110} />
        <Tooltip />
        <Legend />
        {SENTIMENTS.map((sentiment) => (
          <Bar
            key={sentiment}
            dataKey={sentiment}
            name={sentimentLabel(sentiment)}
            stackId="sentiment"
            fill={chartColor(sentiment)}
            isAnimationActive={false}
          />
        ))}
      </BarChart>
    </ChartFigure>
  );
}
