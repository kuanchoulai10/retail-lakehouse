import { createDataTableColumnHelper, DataTable, Panel } from "@retail-lakehouse/design-system";
import type { TableCommitApiResponse } from "@/api/generated/model";
import { formatCount, formatTimestamp } from "@/format";

const column = createDataTableColumnHelper<TableCommitApiResponse>();

const number = (value: number | null) => <span className="block text-right tabular-nums">{formatCount(value)}</span>;
const numberHeader = (label: string) => () => <span className="block text-right">{label}</span>;

const columns = column.columns([
  column.accessor("committed_at", {
    header: "Committed",
    enableSorting: false,
    cell: (info) => <span className="tabular-nums">{formatTimestamp(info.getValue())}</span>,
  }),
  column.accessor("operation", {
    header: "Operation",
    enableSorting: false,
    cell: (info) => <span className="type-code">{info.getValue() ?? "—"}</span>,
  }),
  column.accessor("added_records", {
    header: numberHeader("Added records"),
    enableSorting: false,
    cell: (info) => number(info.getValue()),
  }),
  column.accessor("added_data_files", {
    header: numberHeader("Added files"),
    enableSorting: false,
    cell: (info) => number(info.getValue()),
  }),
]);

export function RecentCommitsPanel({ commits }: { commits: TableCommitApiResponse[] }) {
  const latest = [...commits]
    .sort((a, b) => b.committed_at.localeCompare(a.committed_at))
    .slice(0, 5);
  return (
    <Panel title="Recent commits">
      <DataTable
        caption="Five newest commits"
        columns={columns}
        data={latest}
        getRowId={(commit) => commit.snapshot_id}
        emptyState="No commits yet."
      />
    </Panel>
  );
}
