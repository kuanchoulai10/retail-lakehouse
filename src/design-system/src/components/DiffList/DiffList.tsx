import type { ReactNode } from "react";
import { cn } from "../../lib/cn";
import { Badge } from "../Badge/Badge";
import { Switch } from "../Switch/Switch";

export type DiffChange = "added" | "removed" | "changed" | "unchanged";

export type DiffListItem = {
  id: string;
  change: DiffChange;
  label: ReactNode;
  depth?: number;
  tags?: string[];
  before?: ReactNode;
  after?: ReactNode;
  description?: ReactNode;
};

export type DiffListProps = {
  caption: string;
  items: DiffListItem[];
  onlyChanges: boolean;
  onOnlyChangesChange: (onlyChanges: boolean) => void;
  onlyChangesLabel?: string;
  emptyState?: ReactNode;
  noChangesState?: ReactNode;
  className?: string;
};

const SIGNS: Record<DiffChange, string> = {
  added: "+",
  removed: "−",
  changed: "~",
  unchanged: "",
};

function countText(changes: number): string {
  if (changes === 0) {
    return "No changes";
  }
  return changes === 1 ? "1 change" : `${changes} changes`;
}

function badgesOf(item: DiffListItem): string[] {
  if (item.change === "added") {
    return ["Added"];
  }
  if (item.change === "removed") {
    return ["Removed"];
  }
  return item.change === "changed" ? (item.tags ?? []) : [];
}

function valueOf(item: DiffListItem): ReactNode {
  const hasBefore = item.before !== undefined && item.before !== null;
  const hasAfter = item.after !== undefined && item.after !== null;
  if (hasBefore && hasAfter) {
    return (
      <>
        {item.before}
        <span aria-hidden="true"> {"→"} </span>
        <span className="sr-only"> changed to </span>
        {item.after}
      </>
    );
  }
  return hasAfter ? item.after : item.before;
}

export function DiffList({
  caption,
  items,
  onlyChanges,
  onOnlyChangesChange,
  onlyChangesLabel = "Show changes only",
  emptyState = "Nothing to compare.",
  noChangesState = "No changes.",
  className,
}: DiffListProps) {
  if (items.length === 0) {
    return <p className={cn("type-body-medium py-4 text-on-surface-variant", className)}>{emptyState}</p>;
  }
  const changes = items.filter((item) => item.change !== "unchanged").length;
  const rows = onlyChanges ? items.filter((item) => item.change !== "unchanged") : items;
  return (
    <div className={cn("type-body-medium flex min-w-0 flex-col", className)}>
      <div className="flex flex-wrap items-center justify-between gap-x-4">
        <Switch label={onlyChangesLabel} checked={onlyChanges} onCheckedChange={onOnlyChangesChange} />
        <p className="text-on-surface-variant" aria-live="polite">
          {countText(changes)}
        </p>
      </div>
      {rows.length === 0 ? (
        <p className="py-4 text-on-surface-variant">{noChangesState}</p>
      ) : (
        <ul aria-label={caption} className="divide-y divide-outline border-y border-outline">
          {rows.map((item) => {
            const value = valueOf(item);
            const badges = badgesOf(item);
            return (
              <li
                key={item.id}
                className="flex min-h-row min-w-0 flex-col justify-center py-1 pe-2"
                style={{ paddingInlineStart: `${item.depth ?? 0}rem` }}
              >
                <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 ps-2">
                  <span aria-hidden="true" className="w-4 shrink-0 text-center font-bold">
                    {SIGNS[item.change]}
                  </span>
                  <span
                    className={cn(
                      "type-code min-w-0 break-all",
                      item.change === "removed" && "text-on-surface-variant line-through",
                    )}
                  >
                    {item.label}
                  </span>
                  {badges.map((badge) => (
                    <Badge key={badge}>{badge}</Badge>
                  ))}
                  {value === undefined || value === null ? null : (
                    <span className="min-w-0 break-all text-on-surface-variant">{value}</span>
                  )}
                </div>
                {item.description ? (
                  <p className="ms-6 ps-2 text-on-surface-variant">
                    {item.description}
                  </p>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
