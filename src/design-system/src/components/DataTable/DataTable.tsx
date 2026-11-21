import { useTable, type RowData, type SortingState } from "@tanstack/react-table";
import { Fragment, type ComponentProps, type MouseEvent, type ReactNode } from "react";
import {
  IconArrowDown,
  IconArrowUp,
  IconChevronRight,
  IconSelector,
} from "../../icons";
import { cn } from "../../lib/cn";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../Table/Table";
import { dataTableFeatures, type DataTableColumn } from "./dataTableFeatures";

export type DataTableProps<T extends RowData> = {
  columns: DataTableColumn<T>[];
  data: T[];
  caption: string;
  getRowId?: (row: T, index: number) => string;
  initialSorting?: SortingState;
  emptyState?: ReactNode;
  className?: string;
  /**
   * Names the row in its button: "Expand <label>" / "Collapse <label>", or "Open <label>". Defaults
   * to the row id.
   */
  getRowLabel?: (row: T) => string;
} & (
  | {
      /**
       * Gives every row a detail row below it, opened by a toggle in the first cell or a click on
       * the row. The detail row spans all columns.
       */
      renderDetail?: (row: T) => ReactNode;
      /**
       * Row ids (as given by getRowId) that start expanded. Read once on mount; unknown ids are
       * ignored. Needs renderDetail to show anything.
       */
      initialExpandedRowIds?: string[];
      onOpenRow?: undefined;
      openRowId?: undefined;
    }
  | {
      /**
       * Opens a row somewhere else, such as a side panel: a plain click on the row, or its first
       * cell's button, calls it. A row either expands or opens, so renderDetail is not allowed.
       */
      onOpenRow: (row: T) => void;
      /** The row whose panel is open: its button reads aria-expanded="true" and the row is drawn selected. */
      openRowId?: string | null;
      renderDetail?: undefined;
      initialExpandedRowIds?: undefined;
    }
);

const stickyFirst = "first:sticky first:left-0 first:z-10";
const hoverOverlay =
  "group-hover:bg-[linear-gradient(var(--color-hovered-variant),var(--color-hovered-variant))]";

const ariaSort = { asc: "ascending", desc: "descending" } as const;

const INTERACTIVE = "a, button, input, select, textarea, [role='button'], [role='link']";

// A row click expands the row, or opens its panel, unless it carried a modifier key, landed on a
// control inside the row or ended a text selection, so links, buttons and inputs in cells keep their
// own behaviour and text stays copyable.
function isPlainRowClick(event: MouseEvent<HTMLTableRowElement>): boolean {
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
    return false;
  }
  const target = event.target instanceof Element ? event.target.closest(INTERACTIVE) : null;
  if (target !== null && target !== event.currentTarget && event.currentTarget.contains(target)) {
    return false;
  }
  const selection = event.currentTarget.ownerDocument.getSelection();
  return selection === null || selection.isCollapsed;
}

// The first cell's button, shared by the expand toggle and the button that opens a panel.
function RowButton({
  rotated = false,
  className,
  ...rest
}: ComponentProps<"button"> & { rotated?: boolean }) {
  return (
    <button
      type="button"
      className={cn(
        "-ml-1 inline-flex min-h-row min-w-6 shrink-0 cursor-pointer items-center justify-center rounded-sm",
        "text-on-surface-variant focus-visible:outline-2 focus-visible:outline-offset-2",
        "focus-visible:outline-focus-ring",
        className,
      )}
      {...rest}
    >
      <IconChevronRight aria-hidden="true" className={cn("size-4", rotated && "rotate-90")} />
    </button>
  );
}

export function DataTable<T extends RowData>({
  columns,
  data,
  caption,
  getRowId,
  initialSorting,
  emptyState,
  className,
  renderDetail,
  getRowLabel,
  initialExpandedRowIds,
  onOpenRow,
  openRowId,
}: DataTableProps<T>) {
  const expandable = renderDetail !== undefined;
  const openable = onOpenRow !== undefined;
  const table = useTable({
    features: dataTableFeatures,
    columns,
    data,
    getRowCanExpand: () => expandable,
    autoResetExpanded: false,
    ...(getRowId ? { getRowId } : {}),
    initialState: {
      ...(initialSorting ? { sorting: initialSorting } : {}),
      ...(initialExpandedRowIds
        ? { expanded: Object.fromEntries(initialExpandedRowIds.map((id) => [id, true])) }
        : {}),
    },
  });
  const rows = table.getRowModel().rows;

  return (
    <div
      role="region"
      aria-label={caption}
      tabIndex={0}
      className={cn(
        "relative overflow-x-auto rounded-lg border border-outline bg-surface",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring",
        className,
      )}
    >
      <Table>
        <caption className="sr-only">{caption}</caption>
        <TableHeader>
          {table.getHeaderGroups().map((group) => (
            <TableRow key={group.id}>
              {group.headers.map((header) => {
                const direction = header.column.getIsSorted();
                const canSort = header.column.getCanSort();
                const content = header.isPlaceholder ? null : <table.FlexRender header={header} />;
                return (
                  <TableHead
                    key={header.id}
                    className={cn(stickyFirst, "first:bg-inverse-primary")}
                    {...(canSort ? { "aria-sort": direction ? ariaSort[direction] : "none" } : {})}
                  >
                    {canSort ? (
                      <button
                        type="button"
                        onClick={header.column.getToggleSortingHandler()}
                        className={cn(
                          "-mx-1 inline-flex min-h-row items-center gap-1 rounded-sm px-1",
                          "cursor-pointer font-semibold",
                          "focus-visible:outline-2 focus-visible:outline-offset-2",
                          "focus-visible:outline-focus-ring",
                        )}
                      >
                        {content}
                        {direction === "asc" ? (
                          <IconArrowUp aria-hidden="true" className="size-4" />
                        ) : direction === "desc" ? (
                          <IconArrowDown aria-hidden="true" className="size-4" />
                        ) : (
                          <IconSelector aria-hidden="true" className="size-4" />
                        )}
                      </button>
                    ) : (
                      content
                    )}
                  </TableHead>
                );
              })}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {rows.map((row) => {
            const expanded = expandable && row.getIsExpanded();
            const label = getRowLabel ? getRowLabel(row.original) : row.id;
            const toggle = (event: MouseEvent) => {
              event.stopPropagation();
              row.toggleExpanded();
            };
            const opened = openable && openRowId === row.id;
            const open = () => onOpenRow?.(row.original);
            return (
              <Fragment key={row.id}>
                <TableRow
                  className={cn(
                    "group",
                    (expandable || openable) && "cursor-pointer",
                    (expanded || opened) && "bg-inverse-primary",
                  )}
                  onClick={
                    expandable || openable
                      ? (event: MouseEvent<HTMLTableRowElement>) => {
                          if (!isPlainRowClick(event)) return;
                          if (openable) {
                            onOpenRow?.(row.original);
                            event.currentTarget.querySelector<HTMLElement>("[data-open-row]")?.focus();
                          } else {
                            row.toggleExpanded();
                          }
                        }
                      : undefined
                  }
                >
                  {row.getAllCells().map((cell, index) => (
                    <TableCell
                      key={cell.id}
                      className={cn(
                        stickyFirst,
                        expanded || opened ? "first:bg-inverse-primary" : "first:bg-surface",
                        hoverOverlay,
                      )}
                    >
                      {index === 0 && (expandable || openable) ? (
                        <span className="inline-flex items-center gap-1">
                          {expandable ? (
                            <RowButton
                              rotated={expanded}
                              aria-expanded={expanded}
                              aria-label={`${expanded ? "Collapse" : "Expand"} ${label}`}
                              onClick={toggle}
                            />
                          ) : (
                            <RowButton
                              data-open-row=""
                              aria-haspopup="dialog"
                              aria-expanded={opened}
                              aria-label={`Open ${label}`}
                              onClick={open}
                            />
                          )}
                          <table.FlexRender cell={cell} />
                        </span>
                      ) : (
                        <table.FlexRender cell={cell} />
                      )}
                    </TableCell>
                  ))}
                </TableRow>
                {expanded ? (
                  <TableRow>
                    <TableCell colSpan={columns.length} className="bg-surface-container">
                      {renderDetail(row.original)}
                    </TableCell>
                  </TableRow>
                ) : null}
              </Fragment>
            );
          })}
          {rows.length === 0 && emptyState !== undefined ? (
            <TableRow>
              <TableCell colSpan={columns.length} className="text-center text-on-surface-variant">
                {emptyState}
              </TableCell>
            </TableRow>
          ) : null}
        </TableBody>
      </Table>
    </div>
  );
}
