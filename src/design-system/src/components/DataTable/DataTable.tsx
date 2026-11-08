import { useTable, type RowData, type SortingState } from "@tanstack/react-table";
import type { ReactNode } from "react";
import {
  SerendieSymbolArrowDown,
  SerendieSymbolArrowUp,
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
}: DataTableProps<T>) {
  const table = useTable({
    features: dataTableFeatures,
    columns,
    data,
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
          {rows.map((row) => (
            <TableRow key={row.id}>
              {row.getAllCells().map((cell) => (
                <TableCell key={cell.id} className={stickyFirst}>
                  <table.FlexRender cell={cell} />
                </TableCell>
              ))}
            </TableRow>
          ))}
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
