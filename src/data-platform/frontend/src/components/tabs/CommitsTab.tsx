import { Banner, createDataTableColumnHelper, DataTable, Panel } from "@retail-lakehouse/design-system";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api/client";
import type { TableCommitApiResponse, TableCommitsApiResponse } from "@/api/types";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { errorMessage, formatCount, formatTimestamp } from "@/format";
import { writerLabel } from "@/writerLabel";

function sortedNewestFirst(items: TableCommitApiResponse[]): TableCommitApiResponse[] {
  return [...items].sort((a, b) => b.committed_at.localeCompare(a.committed_at));
}

function CommitDetail({ commit }: { commit: TableCommitApiResponse }) {
  return (
    <>
      <p className="type-code">Snapshot id: {commit.snapshot_id}</p>
      <p className="type-code">Parent id: {commit.parent_id ?? "—"}</p>
      <pre className="type-code mt-2 overflow-x-auto rounded-md bg-surface-container-dim p-2">
        {JSON.stringify(commit.summary, null, 2)}
      </pre>
    </>
  );
}

const column = createDataTableColumnHelper<TableCommitApiResponse>();

const count = (value: number | null) => <span className="block text-right tabular-nums">{formatCount(value)}</span>;
const countHeader = (label: string) => () => <span className="block text-right">{label}</span>;

const columns = column.columns([
  column.accessor("committed_at", {
    header: "Committed",
    enableSorting: false,
    cell: (info) => <span className="tabular-nums whitespace-nowrap">{formatTimestamp(info.getValue())}</span>,
  }),
  column.accessor("operation", {
    header: "Operation",
    enableSorting: false,
    cell: (info) => <span className="font-mono">{info.getValue() ?? "—"}</span>,
  }),
  column.accessor("writer", { header: "Writer", enableSorting: false, cell: (info) => writerLabel(info.getValue()) }),
  column.accessor("added_records", { header: countHeader("Rows added"), enableSorting: false, cell: (info) => count(info.getValue()) }),
  column.accessor("deleted_records", {
    header: countHeader("Rows removed"),
    enableSorting: false,
    cell: (info) => count(info.getValue()),
  }),
  column.accessor("added_data_files", {
    header: countHeader("Files added"),
    enableSorting: false,
    cell: (info) => count(info.getValue()),
  }),
  column.accessor("deleted_data_files", {
    header: countHeader("Files removed"),
    enableSorting: false,
    cell: (info) => count(info.getValue()),
  }),
]);

export function CommitsTab({ tableUuid }: { tableUuid: string }) {
  const commits = useQuery({
    queryKey: ["commits", tableUuid],
    queryFn: () => apiGet<TableCommitsApiResponse>(`/v1/tables/${tableUuid}/commits`),
  });

  if (commits.isPending) return <PanelSkeleton label="Loading commits…" />;
  if (commits.isError) {
    return <Banner type="negative" title={`Could not load commits: ${errorMessage(commits.error)}`} />;
  }
  return (
    <>
      <Panel title="Commits">
        <DataTable
          caption="Commits, newest first"
          columns={columns}
          data={sortedNewestFirst(commits.data.items)}
          getRowId={(commit) => commit.snapshot_id}
          getRowLabel={(commit) => `commit ${commit.snapshot_id}`}
          renderDetail={(commit) => <CommitDetail commit={commit} />}
          emptyState="No commits."
        />
      </Panel>
      {commits.data.truncated && (
        <p className="type-body-small mt-3 text-notice-text">Showing the newest commits only.</p>
      )}
    </>
  );
}
