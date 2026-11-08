import { Table } from "@retail-lakehouse/design-system";
import type { ReactNode } from "react";

// The first cell of each data row; it stays in view while the table scrolls sideways.
export const STICKY_FIRST_CELL = "sticky left-0 z-10 bg-surface";

interface Props {
  caption: string;
  children: ReactNode;
}

// A table whose rows open a detail row below them, which DataTable does not model. It scrolls
// inside its own focusable container, as DataTable does, so a wide table never widens the page.
export function ExpandableRowsTable({ caption, children }: Props) {
  return (
    <div
      role="region"
      aria-label={caption}
      tabIndex={0}
      className="relative overflow-x-auto rounded-lg border border-outline bg-surface focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring"
    >
      <Table>
        <caption className="sr-only">{caption}</caption>
        {children}
      </Table>
    </div>
  );
}
