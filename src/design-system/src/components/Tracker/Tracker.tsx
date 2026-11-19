import { cva } from "class-variance-authority";
import { useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "../../lib/cn";
import { DEFAULT_EMPTY_TEXT } from "../ChartState/ChartState";
import { Tooltip } from "../Tooltip/Tooltip";

export type TrackerItem = {
  key: string;
  status: "positive" | "notice" | "negative" | "neutral";
  label: string;
};

const blockStyle = cva(
  "h-full min-w-0.5 flex-1 rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring",
  {
    variants: {
      status: {
        positive: "bg-positive-text",
        notice: "bg-notice-text",
        negative: "bg-negative-text",
        neutral: "bg-outline-dim",
      },
    },
  },
);

export type TrackerProps = {
  label: string;
  items: readonly TrackerItem[];
  emptyText?: ReactNode;
  className?: string;
};

export function Tracker({ label, items, emptyText = DEFAULT_EMPTY_TEXT, className }: TrackerProps) {
  const [active, setActive] = useState(0);
  const blocks = useRef<(HTMLSpanElement | null)[]>([]);
  if (items.length === 0) {
    return <p className={cn("type-body-medium py-2 text-on-surface-variant", className)}>{emptyText}</p>;
  }
  const current = Math.min(active, items.length - 1);
  const moveTo = (position: number) => {
    const next = Math.min(Math.max(position, 0), items.length - 1);
    setActive(next);
    blocks.current[next]?.focus();
  };
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const target = { ArrowRight: current + 1, ArrowLeft: current - 1, Home: 0, End: items.length - 1 }[event.key];
    if (target !== undefined) {
      event.preventDefault();
      moveTo(target);
    }
  };
  return (
    <div role="group" aria-label={label} onKeyDown={onKeyDown} className={cn("flex h-8 w-full min-w-0 gap-0.5", className)}>
      {items.map((item, position) => (
        <Tooltip key={item.key} content={item.label}>
          <span
            ref={(element) => {
              blocks.current[position] = element;
            }}
            role="img"
            aria-label={item.label}
            tabIndex={position === current ? 0 : -1}
            onFocus={() => setActive(position)}
            className={blockStyle({ status: item.status })}
          />
        </Tooltip>
      ))}
    </div>
  );
}
