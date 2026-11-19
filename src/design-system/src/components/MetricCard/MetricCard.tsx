import { cva } from "class-variance-authority";
import { forwardRef, useId, type ComponentProps, type ReactNode } from "react";
import { IconArrowDown, IconArrowRight, IconArrowUp } from "../../icons";
import { cn } from "../../lib/cn";
import { Skeleton } from "../Skeleton/Skeleton";
import { Sparkline } from "../Sparkline/Sparkline";

export type MetricCardDelta = {
  text: string;
  direction: "up" | "down" | "flat";
  tone: "positive" | "negative" | "neutral";
};

const deltaStyle = cva("type-label-medium flex items-center gap-1", {
  variants: {
    tone: {
      positive: "text-positive-text",
      negative: "text-negative-text",
      neutral: "text-on-surface-variant",
    },
  },
});

const DIRECTION_ICONS = { up: IconArrowUp, down: IconArrowDown, flat: IconArrowRight };

export type MetricCardProps = Omit<ComponentProps<"div">, "children"> & {
  label: string;
  value: ReactNode;
  delta?: MetricCardDelta;
  trend?: readonly number[];
  trendLabel?: string;
  loading?: boolean;
};

export const MetricCard = forwardRef<HTMLDivElement, MetricCardProps>(
  ({ label, value, delta, trend, trendLabel, loading = false, className, ...rest }, ref) => {
    const labelId = useId();
    const DirectionIcon = delta ? DIRECTION_ICONS[delta.direction] : null;
    return (
      <div
        ref={ref}
        role="group"
        aria-labelledby={labelId}
        className={cn("flex min-w-0 flex-col gap-1 rounded-lg border border-outline bg-surface p-4", className)}
        {...rest}
      >
        <p id={labelId} className="type-label-large text-on-surface-variant">
          {label}
        </p>
        {loading ? (
          <div role="status" className="flex flex-col gap-2 py-1">
            <Skeleton className="h-7 w-24" />
            <Skeleton className="h-4 w-16" />
            <span className="sr-only">Loading</span>
          </div>
        ) : (
          <>
            <p className="type-headline-small text-on-surface tabular-nums">{value}</p>
            {delta && DirectionIcon ? (
              <p className={deltaStyle({ tone: delta.tone })}>
                <DirectionIcon size={16} aria-hidden="true" />
                <span>{delta.text}</span>
              </p>
            ) : null}
            {trend ? <Sparkline className="mt-2" label={trendLabel ?? `${label} trend`} data={trend} /> : null}
          </>
        )}
      </div>
    );
  },
);
MetricCard.displayName = "MetricCard";
