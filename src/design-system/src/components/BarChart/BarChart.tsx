import { Bar, BarChart as RechartsBarChart } from "recharts";
import type { CartesianChartProps } from "../../lib/chart/CartesianChartProps";
import { cartesianParts } from "../../lib/chart/cartesianParts";
import { ChartFrame } from "../../lib/chart/ChartFrame";
import { seriesColour } from "../../lib/chart/seriesColour";

export type BarChartProps = CartesianChartProps & {
  stacked?: boolean;
};

export function BarChart({
  label,
  data,
  index,
  series,
  height = 240,
  valueFormatter,
  indexFormatter,
  showLegend = series.length > 1,
  stacked = false,
  loading,
  error,
  emptyText,
  className,
}: BarChartProps) {
  return (
    <ChartFrame
      label={label}
      height={height}
      legend={series.map((item, position) => ({ name: item.name, colour: seriesColour(position) }))}
      showLegend={showLegend}
      loading={loading}
      error={error}
      empty={data.length === 0}
      emptyText={emptyText}
      className={className}
    >
      <RechartsBarChart data={[...data]} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barGap={2}>
        {cartesianParts({ index, valueFormatter, indexFormatter, cursor: "band" })}
        {series.map((item, position) => (
          <Bar
            key={item.key}
            dataKey={item.key}
            name={item.name}
            stackId={stacked ? "stack" : undefined}
            fill={seriesColour(position)}
            radius={stacked ? 0 : [2, 2, 0, 0]}
            maxBarSize={32}
            isAnimationActive={false}
          />
        ))}
      </RechartsBarChart>
    </ChartFrame>
  );
}
