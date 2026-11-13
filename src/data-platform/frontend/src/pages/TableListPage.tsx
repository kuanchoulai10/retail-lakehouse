import {
  Banner,
  createDataTableColumnHelper,
  DataTable,
  MultiSelect,
  Skeleton,
  TextField,
  TextLink,
} from "@retail-lakehouse/design-system";
import { useMemo, useState } from "react";
import { Link } from "react-router";
import type { TableApiResponse } from "@/api/generated/model";
import { useListTables } from "@/api/generated/tables/tables";
import { PageHeader } from "@/components/PageHeader";
import { TableStatusBadge } from "@/components/TableStatusBadge";
import { errorMessage, formatTimestamp } from "@/format";
import { tablePath } from "@/lib/catalogPaths";
import { TABLE_STATUSES, useTableStatusFilter } from "@/lib/useTableStatusFilter";

const SKELETON_ROWS = 5;
const NO_ROWS: TableApiResponse[] = [];

const column = createDataTableColumnHelper<TableApiResponse>();

function fullName(table: TableApiResponse): string {
  return `${table.catalog}.${table.namespace}.${table.table}`;
}

function capitalise(word: string): string {
  return word.charAt(0).toUpperCase() + word.slice(1);
}

const STATUS_ITEMS = TABLE_STATUSES.map((s) => ({ value: s, label: capitalise(s) }));

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
    cell: (info) => <TableStatusBadge status={info.getValue()} />,
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
  const { statuses, setStatuses } = useTableStatusFilter();
  const [search, setSearch] = useState("");
  const tables = useListTables();

  const rows = useMemo((): TableApiResponse[] => {
    const needle = search.trim().toLowerCase();
    return (tables.data ?? NO_ROWS)
      .filter((t) => statuses.some((status) => status === t.status.toLowerCase()))
      .filter((t) => needle === "" || fullName(t).toLowerCase().includes(needle));
  }, [tables.data, statuses, search]);

  return (
    <section>
      <PageHeader title="Tables" />
      <div className="mb-4 grid grid-cols-1 gap-4 sm:flex sm:flex-wrap sm:items-end">
        <MultiSelect
          id="status-filter"
          label="Status"
          items={STATUS_ITEMS}
          value={[...statuses]}
          onValueChange={setStatuses}
          className="sm:w-64"
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
            caption="Tables discovery has found"
            columns={columns}
            data={rows}
            getRowId={(row) => row.uuid}
            initialSorting={[{ id: "name", desc: false }]}
            emptyState={tables.isPending ? <LoadingRows /> : statuses.length === 0 ? "No status selected." : "No tables match."}
          />
        </div>
      )}
    </section>
  );
}
