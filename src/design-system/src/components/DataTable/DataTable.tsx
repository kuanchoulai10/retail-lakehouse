import { useTable, type RowData, type SortingState } from "@tanstack/react-table";
import { Fragment, type MouseEvent, type ReactNode } from "react";
import {
  SerendieSymbolArrowDown,
  SerendieSymbolArrowUp,
  SerendieSymbolChevronRight,
  SerendieSymbolChevronUpDown,
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
   * Gives every row a detail row below it, opened by a toggle in the first cell or a click on
   * the row. The detail row spans all columns.
   */
  renderDetail?: (row: T) => ReactNode;
  /** Names the row in its toggle: "Expand <label>" / "Collapse <label>". Defaults to the row id. */
  getRowLabel?: (row: T) => string;
};

const stickyFirst = "first:sticky first:left-0 first:z-10 first:bg-surface";

const ariaSort = { asc: "ascending", desc: "descending" } as const;

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
}: DataTableProps<T>) {
  const expandable = renderDetail !== undefined;
  const table = useTable({
    features: dataTableFeatures,
    columns,
    data,
    getRowCanExpand: () => expandable,
    autoResetExpanded: false,
    ...(getRowId ? { getRowId } : {}),
    ...(initialSorting ? { initialState: { sorting: initialSorting } } : {}),
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
                    className={stickyFirst}
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
                          <SerendieSymbolArrowUp aria-hidden="true" className="size-4" />
                        ) : direction === "desc" ? (
                          <SerendieSymbolArrowDown aria-hidden="true" className="size-4" />
                        ) : (
                          <SerendieSymbolChevronUpDown aria-hidden="true" className="size-4" />
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
            return (
              <Fragment key={row.id}>
                <TableRow
                  className={expandable ? "cursor-pointer" : undefined}
                  onClick={expandable ? () => row.toggleExpanded() : undefined}
                >
                  {row.getAllCells().map((cell, index) => (
                    <TableCell key={cell.id} className={stickyFirst}>
                      {expandable && index === 0 ? (
                        <span className="inline-flex items-center gap-1">
                          <button
                            type="button"
                            aria-expanded={expanded}
                            aria-label={`${expanded ? "Collapse" : "Expand"} ${label}`}
                            onClick={toggle}
                            className={cn(
                              "-ml-1 inline-flex min-h-row min-w-6 shrink-0 cursor-pointer items-center justify-center rounded-sm",
                              "text-on-surface-variant focus-visible:outline-2 focus-visible:outline-offset-2",
                              "focus-visible:outline-focus-ring",
                            )}
                          >
                            <SerendieSymbolChevronRight
                              aria-hidden="true"
                              className={cn("size-4", expanded && "rotate-90")}
                            />
                          </button>
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
