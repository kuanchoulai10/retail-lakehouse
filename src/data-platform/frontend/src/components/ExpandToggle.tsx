import { cn, SerendieSymbolChevronRight } from "@retail-lakehouse/design-system";
import type { ReactNode } from "react";

interface Props {
  open: boolean;
  label: string;
  children: ReactNode;
}

// The button in an expandable row's first cell; the row's own click toggles it too.
export function ExpandToggle({ open, label, children }: Props) {
  return (
    <button
      type="button"
      aria-expanded={open}
      aria-label={label}
      className="inline-flex min-h-row cursor-pointer items-center gap-1 rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring"
    >
      <SerendieSymbolChevronRight
        aria-hidden="true"
        className={cn("size-4 shrink-0 text-on-surface-variant", open && "rotate-90")}
      />
      {children}
    </button>
  );
}
