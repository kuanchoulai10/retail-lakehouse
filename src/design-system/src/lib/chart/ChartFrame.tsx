import type { ReactElement, ReactNode } from "react";
import { ChartContainer } from "../../components/ChartContainer/ChartContainer";
import { ChartLegend, type ChartLegendItem } from "../../components/ChartLegend/ChartLegend";
import { ChartState } from "../../components/ChartState/ChartState";
import { cn } from "../cn";

export type ChartFrameProps = {
  label: string;
  height: number;
  legend: readonly ChartLegendItem[];
  showLegend: boolean;
  loading?: boolean;
  error?: string;
  empty: boolean;
  emptyText?: ReactNode;
  className?: string;
  children: ReactElement;
};

export function ChartFrame({
  label,
  height,
  legend,
  showLegend,
  loading,
  error,
  empty,
  emptyText,
  className,
  children,
}: ChartFrameProps) {
  const ready = !loading && !error && !empty;
  return (
    <div className={cn("flex w-full min-w-0 flex-col gap-3", className)}>
      <ChartState height={height} loading={loading} error={error} empty={empty} emptyText={emptyText}>
        <ChartContainer
          label={label}
          height={height}
          className={cn(
            "type-body-small",
            "[&_.recharts-surface]:rounded-sm [&_.recharts-surface:focus]:outline-none",
            "[&_.recharts-surface:focus-visible]:outline-2 [&_.recharts-surface:focus-visible]:outline-offset-2 [&_.recharts-surface:focus-visible]:outline-focus-ring",
          )}
        >
          {children}
        </ChartContainer>
      </ChartState>
      {ready && showLegend ? <ChartLegend items={legend} /> : null}
    </div>
  );
}
