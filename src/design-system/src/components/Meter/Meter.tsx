import { cva } from "class-variance-authority";
import { useId } from "react";
import { cn } from "../../lib/cn";

const fillStyle = cva("", {
  variants: {
    variant: { bar: "", ring: "" },
    tone: { default: "", positive: "", notice: "", negative: "" },
  },
  compoundVariants: [
    { variant: "bar", tone: "default", className: "bg-primary" },
    { variant: "bar", tone: "positive", className: "bg-positive-text" },
    { variant: "bar", tone: "notice", className: "bg-notice-text" },
    { variant: "bar", tone: "negative", className: "bg-negative-text" },
    { variant: "ring", tone: "default", className: "stroke-primary" },
    { variant: "ring", tone: "positive", className: "stroke-positive-text" },
    { variant: "ring", tone: "notice", className: "stroke-notice-text" },
    { variant: "ring", tone: "negative", className: "stroke-negative-text" },
  ],
});

export type MeterProps = {
  label: string;
  value: number;
  max?: number;
  valueText?: string;
  variant?: "bar" | "ring";
  tone?: "default" | "positive" | "notice" | "negative";
  className?: string;
};

const RING_RADIUS = 100 / (2 * Math.PI);

export function Meter({
  label,
  value,
  max = 100,
  valueText = String(value),
  variant = "bar",
  tone = "default",
  className,
}: MeterProps) {
  const labelId = useId();
  const share = Math.round(Math.min(Math.max(value / max, 0), 1) * 100);
  const meterProps = {
    role: "meter",
    "aria-labelledby": labelId,
    "aria-valuenow": value,
    "aria-valuemin": 0,
    "aria-valuemax": max,
    "aria-valuetext": valueText,
  } as const;
  if (variant === "ring") {
    return (
      <div className={cn("inline-flex flex-col items-center gap-2", className)}>
        <div {...meterProps} className="relative size-20">
          <svg viewBox="0 0 36 36" className="size-full -rotate-90" aria-hidden="true">
            <circle cx="18" cy="18" r={RING_RADIUS} fill="none" strokeWidth="3.5" className="stroke-surface-container-dim" />
            <circle
              data-meter-fill=""
              cx="18"
              cy="18"
              r={RING_RADIUS}
              fill="none"
              strokeWidth="3.5"
              strokeDasharray={`${share} 100`}
              className={fillStyle({ variant, tone })}
            />
          </svg>
          <span className="type-label-large absolute inset-0 flex items-center justify-center text-on-surface tabular-nums">
            {valueText}
          </span>
        </div>
        <span id={labelId} className="type-body-small text-on-surface-variant">
          {label}
        </span>
      </div>
    );
  }
  return (
    <div className={cn("flex w-full min-w-0 flex-col gap-1.5", className)}>
      <div className="type-body-small flex items-baseline justify-between gap-3">
        <span id={labelId} className="min-w-0 truncate text-on-surface-variant">
          {label}
        </span>
        <span className="shrink-0 font-bold text-on-surface tabular-nums">{valueText}</span>
      </div>
      <div {...meterProps} className="h-2 w-full overflow-hidden rounded-sm bg-surface-container-dim">
        <div data-meter-fill="" className={cn("h-full rounded-sm", fillStyle({ variant, tone }))} style={{ width: `${share}%` }} />
      </div>
    </div>
  );
}
