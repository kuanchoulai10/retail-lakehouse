import type { ReactNode } from "react";
import { Cell, Pie, PieChart, Tooltip as RechartsTooltip } from "recharts";
import { cn } from "../../lib/cn";
import { formatChartNumber } from "../../lib/chart/formatChartNumber";
import { seriesColour } from "../../lib/chart/seriesColour";
import { ChartContainer } from "../ChartContainer/ChartContainer";
import { ChartLegend } from "../ChartLegend/ChartLegend";
import { ChartState } from "../ChartState/ChartState";
import { ChartTooltip } from "../ChartTooltip/ChartTooltip";

export type DonutChartSlice = {
  name: string;
  value: number;
};

export type DonutChartProps = {
  label: string;
  data: readonly DonutChartSlice[];
  size?: number;
  centerLabel?: ReactNode;
  valueFormatter?: (value: number) => string;
  loading?: boolean;
  error?: string;
  emptyText?: ReactNode;
  className?: string;
};

export function DonutChart({
  label,
  data,
  size = 160,
  centerLabel,
  valueFormatter = formatChartNumber,
  loading,
  error,
  emptyText,
  className,
}: DonutChartProps) {
  return (
    <ChartState height={size} loading={loading} error={error} empty={data.length === 0} emptyText={emptyText}>
      <div className={cn("flex w-full min-w-0 flex-wrap items-center gap-6", className)}>
        <div className="relative shrink-0" style={{ width: size }}>
          <ChartContainer label={label} height={size}>
            <PieChart accessibilityLayer={false}>
              <Pie
                data={[...data]}
                dataKey="value"
                nameKey="name"
                innerRadius="72%"
                outerRadius="100%"
                paddingAngle={1}
                stroke="var(--color-surface)"
                isAnimationActive={false}
              >
                {data.map((slice, position) => (
                  <Cell key={slice.name} fill={seriesColour(position)} />
                ))}
              </Pie>
              <RechartsTooltip isAnimationActive={false} content={<ChartTooltip valueFormatter={valueFormatter} />} />
            </PieChart>
          </ChartContainer>
          {centerLabel === undefined ? null : (
            <p
              aria-hidden="true"
              className="type-title-medium pointer-events-none absolute inset-0 flex items-center justify-center text-on-surface"
            >
              {centerLabel}
            </p>
          )}
        </div>
        <ChartLegend
          className="min-w-40 flex-1 flex-col"
          items={data.map((slice, position) => ({
            name: slice.name,
            colour: seriesColour(position),
            value: valueFormatter(slice.value),
          }))}
        />
      </div>
    </ChartState>
  );
}
