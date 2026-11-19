import { Area, AreaChart as RechartsAreaChart } from "recharts";
import type { CartesianChartProps } from "../../lib/chart/CartesianChartProps";
import { cartesianParts } from "../../lib/chart/cartesianParts";
import { ChartFrame } from "../../lib/chart/ChartFrame";
import { seriesColour } from "../../lib/chart/seriesColour";

export type AreaChartProps = CartesianChartProps & {
  stacked?: boolean;
};

export function AreaChart({
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
}: AreaChartProps) {
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
      <RechartsAreaChart data={[...data]} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        {cartesianParts({ index, valueFormatter, indexFormatter, cursor: "line" })}
        {series.map((item, position) => (
          <Area
            key={item.key}
            type="monotone"
            dataKey={item.key}
            name={item.name}
            stackId={stacked ? "stack" : undefined}
            stroke={seriesColour(position)}
            fill={seriesColour(position)}
            fillOpacity={1}
            strokeWidth={2}
            activeDot={{ r: 4, strokeWidth: 0 }}
            isAnimationActive={false}
          />
        ))}
      </RechartsAreaChart>
    </ChartFrame>
  );
}
