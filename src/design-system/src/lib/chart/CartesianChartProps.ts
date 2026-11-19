import type { ReactNode } from "react";
import type { ChartSeries } from "./ChartSeries";

export type CartesianChartProps = {
  label: string;
  data: readonly Record<string, unknown>[];
  index: string;
  series: readonly ChartSeries[];
  height?: number;
  valueFormatter?: (value: number) => string;
  indexFormatter?: (value: unknown) => string;
  showLegend?: boolean;
  loading?: boolean;
  error?: string;
  emptyText?: ReactNode;
  className?: string;
};
