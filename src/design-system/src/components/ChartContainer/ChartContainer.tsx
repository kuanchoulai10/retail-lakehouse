import type { ReactElement } from "react";
import { ResponsiveContainer } from "recharts";
import { cn } from "../../lib/cn";

export const CHART_COLOURS = [
  "var(--color-chart-1)",
  "var(--color-chart-2)",
  "var(--color-chart-3)",
  "var(--color-chart-4)",
  "var(--color-chart-5)",
] as const;

export type ChartContainerProps = {
  label: string;
  height: number;
  children: ReactElement;
  className?: string;
};

export function ChartContainer({ label, height, children, className }: ChartContainerProps) {
  return (
    <div
      role="img"
      aria-label={label}
      className={cn("w-full min-w-0 text-on-surface-variant", className)}
      style={{ height }}
    >
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  );
}
