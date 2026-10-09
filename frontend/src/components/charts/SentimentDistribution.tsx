import { Bar, BarChart, CartesianGrid, Cell, LabelList, Tooltip, XAxis, YAxis } from "recharts";

import { chartColor, SENTIMENTS, sentimentLabel } from "../../lib/sentiment";
import type { SentimentCounts } from "../../types/api";
import ChartFigure from "./ChartFigure";

interface Props {
  counts: SentimentCounts;
  total: number;
}

/** How many reviews are positive, neutral and negative overall. */
export default function SentimentDistribution({ counts, total }: Props) {
  const data = SENTIMENTS.map((sentiment) => ({
    sentiment,
    name: sentimentLabel(sentiment),
    count: counts[sentiment],
  }));
  const words = data.map((d) => `${d.count} ${d.sentiment}`).join(", ");
  return (
    <ChartFigure
      title="Overall sentiment of the reviews"
      description={`Overall sentiment of ${total} reviews: ${words}`}
    >
      <BarChart data={data} margin={{ top: 16, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="name" />
        <YAxis allowDecimals={false} />
        <Tooltip />
        <Bar dataKey="count" name="Reviews" isAnimationActive={false}>
          {data.map((d) => (
            <Cell key={d.sentiment} fill={chartColor(d.sentiment)} />
          ))}
          <LabelList dataKey="count" position="top" />
        </Bar>
      </BarChart>
    </ChartFigure>
  );
}
