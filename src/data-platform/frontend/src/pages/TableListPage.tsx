import { useQuery } from "@tanstack/react-query";
import {
  createColumnHelper,
  createSortedRowModel,
  rowSortingFeature,
  sortFn_datetime,
  sortFn_text,
  tableFeatures,
  useTable,
  type SortingState,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router";
import { apiGet } from "@/api/client";
import type { TableApiResponse } from "@/api/types";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { errorMessage, formatTimestamp } from "@/format";
import { cn } from "@/lib/utils";

const ALL_STATUSES = "all";
const STATUSES = ["active", "paused", "excluded", "dropped"] as const;
const COLUMN_COUNT = 5;
const SKELETON_ROWS = 5;
const NO_ROWS: TableApiResponse[] = [];

const features = tableFeatures({
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns: { text: sortFn_text, datetime: sortFn_datetime },
});
const columnHelper = createColumnHelper<typeof features, TableApiResponse>();

function fullName(table: TableApiResponse): string {
  return `${table.catalog}.${table.namespace}.${table.table}`;
}

function capitalise(word: string): string {
  return word.charAt(0).toUpperCase() + word.slice(1);
}

const columns = columnHelper.columns([
  columnHelper.accessor((t) => fullName(t), {
    id: "name",
    header: "Name",
    sortFn: "text",
    cell: (info) => (
      <Link
        to={`/tables/${info.row.original.uuid}`}
        className="font-mono text-[13px] font-medium hover:underline"
      >
        {info.getValue()}
      </Link>
    ),
  }),
  columnHelper.accessor((t) => t.status, {
    id: "status",
    header: "Status",
    sortFn: "text",
    cell: (info) => <StatusBadge status={info.getValue()} />,
  }),
  columnHelper.accessor((t) => t.selection, {
    id: "selection",
    header: "Selection",
    sortFn: "text",
  }),
  columnHelper.accessor((t) => t.source_preset_id ?? "", {
    id: "source_preset",
    header: "Source preset",
    sortFn: "text",
    cell: (info) => info.getValue() || "—",
  }),
  columnHelper.accessor((t) => t.updated_at, {
    id: "updated_at",
    header: "Updated",
    sortFn: "datetime",
    sortDescFirst: true,
    cell: (info) => (
      <time dateTime={info.getValue()} className="tabular-nums">
        {formatTimestamp(info.getValue())}
      </time>
    ),
  }),
]);

function SortIcon({ direction }: { direction: false | "asc" | "desc" }) {
  if (direction === "asc") return <ArrowUp className="size-3.5" aria-hidden />;
  if (direction === "desc") return <ArrowDown className="size-3.5" aria-hidden />;
  return <ChevronsUpDown className="size-3.5 text-muted-foreground" aria-hidden />;
}

export function TableListPage() {
  const [status, setStatus] = useState(ALL_STATUSES);
  const [search, setSearch] = useState("");
  const [sorting, setSorting] = useState<SortingState>([{ id: "name", desc: false }]);
  const tables = useQuery({
    queryKey: ["tables"],
    queryFn: () => apiGet<TableApiResponse[]>("/v1/tables"),
  });

  const rows = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return (tables.data ?? NO_ROWS)
      .filter((t) => status === ALL_STATUSES || t.status.toLowerCase() === status)
      .filter((t) => needle === "" || fullName(t).toLowerCase().includes(needle));
  }, [tables.data, status, search]);

  const table = useTable({
    features,
    columns,
    data: rows,
    state: { sorting },
    onSortingChange: setSorting,
  });

  return (
    <section>
      <PageHeader title="Tables" />
      <div className="mb-4 flex flex-wrap items-end gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="status-filter">Status</Label>
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger id="status-filter" className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_STATUSES}>All</SelectItem>
              {STATUSES.map((s) => (
                <SelectItem key={s} value={s}>
                  {capitalise(s)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="table-search">Search</Label>
          <Input
            id="table-search"
            type="search"
            placeholder="catalog.namespace.table"
            className="w-72"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>
      {tables.isError && (
        <Alert variant="destructive">
          <AlertDescription>Could not load tables: {errorMessage(tables.error)}</AlertDescription>
        </Alert>
      )}
      {!tables.isError && (
        <div aria-busy={tables.isPending} className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              {table.getHeaderGroups().map((group) => (
                <TableRow key={group.id}>
                  {group.headers.map((header) => {
                    const direction = header.column.getIsSorted();
                    return (
                      <TableHead
                        key={header.id}
                        aria-sort={
                          direction === "asc"
                            ? "ascending"
                            : direction === "desc"
                              ? "descending"
                              : "none"
                        }
                      >
                        <button
                          type="button"
                          className={cn(
                            "inline-flex cursor-pointer items-center gap-1 rounded-md font-medium",
                            "hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 outline-none",
                          )}
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          {header.column.columnDef.header as string}
                          <SortIcon direction={direction} />
                        </button>
                      </TableHead>
                    );
                  })}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {tables.isPending &&
                Array.from({ length: SKELETON_ROWS }, (_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: COLUMN_COUNT }, (_, j) => (
                      <TableCell key={j}>
                        <Skeleton className="h-4 w-full max-w-40" />
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              {tables.isSuccess &&
                table.getRowModel().rows.map((row) => (
                  <TableRow key={row.original.uuid}>
                    {row.getAllCells().map((cell) => (
                      <TableCell key={cell.id}>
                        <table.FlexRender cell={cell} />
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              {tables.isSuccess && rows.length === 0 && (
                <TableRow>
                  <TableCell colSpan={COLUMN_COUNT} className="text-center text-muted-foreground">
                    No tables match.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      )}
    </section>
  );
}
