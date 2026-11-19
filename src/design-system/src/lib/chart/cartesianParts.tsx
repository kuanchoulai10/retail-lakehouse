import { CartesianGrid, Tooltip as RechartsTooltip, XAxis, YAxis } from "recharts";
import { ChartTooltip } from "../../components/ChartTooltip/ChartTooltip";
import { formatChartNumber } from "./formatChartNumber";

const TICK = { fill: "var(--color-on-surface-variant)" };

export type CartesianPartsOptions = {
  index: string;
  valueFormatter?: (value: number) => string;
  indexFormatter?: (value: unknown) => string;
  cursor: "line" | "band";
};

export function cartesianParts({
  index,
  valueFormatter = formatChartNumber,
  indexFormatter = String,
  cursor,
}: CartesianPartsOptions) {
  return [
    <CartesianGrid key="grid" vertical={false} stroke="var(--color-outline)" />,
    <XAxis
      key="x"
      dataKey={index}
      tickFormatter={(value: unknown) => indexFormatter(value)}
      axisLine={false}
      tickLine={false}
      tick={TICK}
      minTickGap={24}
    />,
    <YAxis
      key="y"
      width="auto"
      tickFormatter={(value: number) => valueFormatter(value)}
      axisLine={false}
      tickLine={false}
      tick={TICK}
    />,
    <RechartsTooltip
      key="tooltip"
      isAnimationActive={false}
      cursor={cursor === "line" ? { stroke: "var(--color-outline-dim)" } : { fill: "var(--color-hovered-variant)" }}
      content={<ChartTooltip valueFormatter={valueFormatter} labelFormatter={indexFormatter} />}
    />,
  ];
}
