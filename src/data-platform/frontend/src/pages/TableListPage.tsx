import {
  Banner,
  createDataTableColumnHelper,
  DataTable,
  Select,
  Skeleton,
  TextField,
  TextLink,
} from "@retail-lakehouse/design-system";
import { useMemo, useState } from "react";
import { Link } from "react-router";
import type { TableApiResponse } from "@/api/generated/model";
import { useGetTableDiscoveryRules } from "@/api/generated/discovery-rules/discovery-rules";
import { useListTables } from "@/api/generated/tables/tables";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { errorMessage, formatTimestamp } from "@/format";
import { tablePath } from "@/lib/catalogPaths";

const ALL_STATUSES = "all";
const STATUSES = ["managed", "unmanaged", "dropped"] as const;
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

// The rule column names a rule by its priority; rules have no names, and their globs are too long for a cell.
function tableColumns(priorities: Map<string, number>) {
  return column.columns([
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
    // The discovery rule that manages the table; an unmanaged or dropped table has none.
    column.accessor((t) => (t.matched_rule_id === null ? undefined : priorities.get(t.matched_rule_id)), {
      id: "matched_rule",
      header: "Rule",
      sortFn: "basic",
      sortUndefined: "last",
      cell: (info) => {
        const priority = info.getValue();
        if (priority === undefined) return "—";
        return (
          <TextLink asChild className="tabular-nums">
            <Link to="/discovery-rules">{`Priority ${priority}`}</Link>
          </TextLink>
        );
      },
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
}

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
  const tables = useListTables();
  const rules = useGetTableDiscoveryRules();
  const columns = useMemo(
    () => tableColumns(new Map((rules.data?.rules ?? []).map((rule) => [rule.id, rule.priority]))),
    [rules.data],
  );

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
            caption="Tables discovery has found"
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
