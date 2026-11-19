import { Area, AreaChart, Line, LineChart, YAxis } from "recharts";
import { seriesColour } from "../../lib/chart/seriesColour";
import { ChartContainer } from "../ChartContainer/ChartContainer";

export type SparklineProps = {
  label: string;
  data: readonly number[];
  height?: number;
  area?: boolean;
  className?: string;
};

export function Sparkline({ label, data, height = 32, area = false, className }: SparklineProps) {
  const points = data.map((value, step) => ({ step, value }));
  const colour = seriesColour(0);
  const margin = { top: 2, right: 2, bottom: 2, left: 2 };
  const domain = <YAxis hide domain={["dataMin", "dataMax"]} />;
  return (
    <ChartContainer label={label} height={height} className={className}>
      {area ? (
        <AreaChart data={points} margin={margin} accessibilityLayer={false}>
          {domain}
          <Area
            type="monotone"
            dataKey="value"
            stroke={colour}
            fill={colour}
            fillOpacity={1}
            strokeWidth={1.5}
            baseValue="dataMin"
            isAnimationActive={false}
          />
        </AreaChart>
      ) : (
        <LineChart data={points} margin={margin} accessibilityLayer={false}>
          {domain}
          <Line type="monotone" dataKey="value" stroke={colour} strokeWidth={1.5} dot={false} isAnimationActive={false} />
        </LineChart>
      )}
    </ChartContainer>
  );
}
