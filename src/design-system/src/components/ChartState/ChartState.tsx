import type { ReactNode } from "react";
import { cn } from "../../lib/cn";
import { Skeleton } from "../Skeleton/Skeleton";

export const DEFAULT_EMPTY_TEXT = "No data in this time range";

export type ChartStateProps = {
  height: number;
  loading?: boolean;
  error?: string;
  empty?: boolean;
  emptyText?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function ChartState({
  height,
  loading = false,
  error,
  empty = false,
  emptyText = DEFAULT_EMPTY_TEXT,
  children,
  className,
}: ChartStateProps) {
  if (loading) {
    return (
      <div role="status" className={cn("relative w-full", className)} style={{ height }}>
        <Skeleton className="size-full" />
        <span className="sr-only">Loading chart</span>
      </div>
    );
  }
  if (error) {
    return (
      <div
        role="alert"
        className={cn("flex w-full items-center justify-center px-4 text-center", className)}
        style={{ height }}
      >
        <p className="type-body-medium text-negative-text">{error}</p>
      </div>
    );
  }
  if (empty) {
    return (
      <div className={cn("flex w-full items-center justify-center px-4 text-center", className)} style={{ height }}>
        <p className="type-body-medium text-on-surface-variant">{emptyText}</p>
      </div>
    );
  }
  return <>{children}</>;
}
