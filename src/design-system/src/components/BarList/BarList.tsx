import type { ReactNode } from "react";
import { cn } from "../../lib/cn";
import { formatChartNumber } from "../../lib/chart/formatChartNumber";
import { DEFAULT_EMPTY_TEXT } from "../ChartState/ChartState";

export type BarListItem = {
  name: string;
  value: number;
};

export type BarListProps<Item extends BarListItem = BarListItem> = {
  label: string;
  items: readonly Item[];
  valueFormatter?: (value: number) => string;
  sorted?: boolean;
  onSelect?: (item: Item) => void;
  emptyText?: ReactNode;
  className?: string;
};

export function BarList<Item extends BarListItem>({
  label,
  items,
  valueFormatter = formatChartNumber,
  sorted = true,
  onSelect,
  emptyText = DEFAULT_EMPTY_TEXT,
  className,
}: BarListProps<Item>) {
  if (items.length === 0) {
    return <p className={cn("type-body-medium py-4 text-on-surface-variant", className)}>{emptyText}</p>;
  }
  const rows = sorted ? [...items].sort((left, right) => right.value - left.value) : items;
  const largest = Math.max(...rows.map((item) => item.value));
  return (
    <ul aria-label={label} className={cn("type-body-medium flex min-w-0 flex-col gap-1", className)}>
      {rows.map((item) => {
        const share = largest > 0 ? Math.round((item.value / largest) * 100) : 0;
        const content = (
          <>
            <span
              data-bar=""
              aria-hidden="true"
              className="absolute inset-y-1 left-0 rounded-sm bg-inverse-primary"
              style={{ width: `${share}%` }}
            />
            <span className="relative min-w-0 truncate">{item.name}</span>
            <span className="relative shrink-0 font-bold tabular-nums">{valueFormatter(item.value)}</span>
          </>
        );
        const rowStyle = "relative flex min-h-control w-full items-center justify-between gap-3 rounded-sm px-2 text-on-surface";
        return (
          <li key={item.name}>
            {onSelect ? (
              <button
                type="button"
                onClick={() => onSelect(item)}
                className={cn(
                  rowStyle,
                  "cursor-pointer text-left hover:bg-hovered-variant",
                  "focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-focus-ring",
                )}
              >
                {content}
              </button>
            ) : (
              <div className={rowStyle}>{content}</div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
