import { Line, LineChart as RechartsLineChart } from "recharts";
import type { CartesianChartProps } from "../../lib/chart/CartesianChartProps";
import { cartesianParts } from "../../lib/chart/cartesianParts";
import { ChartFrame } from "../../lib/chart/ChartFrame";
import { seriesColour } from "../../lib/chart/seriesColour";

export type LineChartProps = CartesianChartProps;

export function LineChart({
  label,
  data,
  index,
  series,
  height = 240,
  valueFormatter,
  indexFormatter,
  showLegend = series.length > 1,
  loading,
  error,
  emptyText,
  className,
}: LineChartProps) {
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
      <RechartsLineChart data={[...data]} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        {cartesianParts({ index, valueFormatter, indexFormatter, cursor: "line" })}
        {series.map((item, position) => (
          <Line
            key={item.key}
            type="monotone"
            dataKey={item.key}
            name={item.name}
            stroke={seriesColour(position)}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0 }}
            isAnimationActive={false}
          />
        ))}
      </RechartsLineChart>
    </ChartFrame>
  );
}
