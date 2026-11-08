import {
  Banner,
  createDataTableColumnHelper,
  DataTable,
  Select,
  Skeleton,
  TextField,
  TextLink,
} from "@retail-lakehouse/design-system";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router";
import { apiGet } from "@/api/client";
import type { TableApiResponse } from "@/api/types";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { errorMessage, formatTimestamp } from "@/format";
import { tablePath } from "@/lib/catalogPaths";

const ALL_STATUSES = "all";
const STATUSES = ["active", "paused", "excluded", "dropped"] as const;
const SKELETON_ROWS = 5;
const NO_ROWS: TableApiResponse[] = [];

const column = createDataTableColumnHelper<TableApiResponse>();

function fullName(table: TableApiResponse): string {
  return `${table.catalog}.${table.namespace}.${table.table}`;
}

function capitalise(word: string): string {
  return word.charAt(0).toUpperCase() + word.slice(1);
}

const STATUS_ITEMS = [
  { value: ALL_STATUSES, label: "All" },
  ...STATUSES.map((s) => ({ value: s, label: capitalise(s) })),
];

const columns = column.columns([
  column.accessor((t) => fullName(t), {
    id: "name",
    header: "Name",
    sortFn: "text",
    // Maintenance stores the namespace levels joined with "."; a dropped table has no page.
    cell: (info) => {
      const row = info.row.original;
      if (row.status.toLowerCase() === "dropped") {
        return <span className="font-mono font-medium">{info.getValue()}</span>;
      }
      return (
        <TextLink asChild className="font-mono font-medium">
          <Link to={tablePath(row.catalog, row.namespace.split("."), row.table)}>
            {info.getValue()}
          </Link>
        </TextLink>
      );
    },
  }),
  column.accessor((t) => t.status, {
    id: "status",
    header: "Status",
    sortFn: "text",
    cell: (info) => <StatusBadge status={info.getValue()} />,
  }),
  column.accessor((t) => t.selection, {
    id: "selection",
    header: "Selection",
    sortFn: "text",
  }),
  column.accessor((t) => t.source_preset_id ?? "", {
    id: "source_preset",
    header: "Source preset",
    sortFn: "text",
    cell: (info) => info.getValue() || "—",
  }),
  column.accessor((t) => t.updated_at, {
    id: "updated_at",
    header: "Updated",
    sortFn: "datetime",
    sortDescFirst: true,
    cell: (info) => (
      <time dateTime={info.getValue()} className="tabular-nums whitespace-nowrap">
        {formatTimestamp(info.getValue())}
      </time>
    ),
  }),
]);

function LoadingRows() {
  return (
    <div className="grid gap-3 py-1">
      {Array.from({ length: SKELETON_ROWS }, (_, i) => (
        <Skeleton key={i} className="h-4 w-full" />
      ))}
    </div>
  );
}

export function TableListPage() {
  const [status, setStatus] = useState(ALL_STATUSES);
  const [search, setSearch] = useState("");
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

  return (
    <section>
      <PageHeader title="Tables" />
      <div className="mb-4 grid grid-cols-1 gap-4 sm:flex sm:flex-wrap sm:items-end">
        <Select
          id="status-filter"
          label="Status"
          items={STATUS_ITEMS}
          value={status}
          onValueChange={setStatus}
          className="sm:w-40"
        />
        <TextField
          id="table-search"
          label="Search"
          type="search"
          placeholder="catalog.namespace.table"
          className="sm:w-72"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      {tables.isError && (
        <Banner type="negative" title={`Could not load tables: ${errorMessage(tables.error)}`} />
      )}
      {!tables.isError && (
        <div aria-busy={tables.isPending}>
          <DataTable
            caption="Tables maintenance manages"
            columns={columns}
            data={rows}
            getRowId={(row) => row.uuid}
            initialSorting={[{ id: "name", desc: false }]}
            emptyState={tables.isPending ? <LoadingRows /> : "No tables match."}
          />
        </div>
      )}
    </section>
  );
}
