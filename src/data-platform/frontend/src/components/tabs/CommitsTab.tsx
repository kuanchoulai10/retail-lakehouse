import {
  Banner,
  Panel,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@retail-lakehouse/design-system";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { apiGet } from "@/api/client";
import type { TableCommitApiResponse, TableCommitsApiResponse } from "@/api/types";
import { ExpandableRowsTable, STICKY_FIRST_CELL } from "@/components/ExpandableRowsTable";
import { ExpandToggle } from "@/components/ExpandToggle";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { errorMessage, formatCount, formatTimestamp } from "@/format";
import { writerLabel } from "@/writerLabel";

function sortedNewestFirst(items: TableCommitApiResponse[]): TableCommitApiResponse[] {
  return [...items].sort((a, b) => b.committed_at.localeCompare(a.committed_at));
}

function CommitRow({ commit }: { commit: TableCommitApiResponse }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <TableRow data-testid="commit-row" className="cursor-pointer" onClick={() => setOpen(!open)}>
        <TableCell className={STICKY_FIRST_CELL}>
          <ExpandToggle open={open} label={`${open ? "Collapse" : "Expand"} commit ${commit.snapshot_id}`}>
            <span className="tabular-nums whitespace-nowrap">{formatTimestamp(commit.committed_at)}</span>
          </ExpandToggle>
        </TableCell>
        <TableCell className="font-mono">{commit.operation ?? "—"}</TableCell>
        <TableCell>{writerLabel(commit.writer)}</TableCell>
        <TableCell numeric>{formatCount(commit.added_records)}</TableCell>
        <TableCell numeric>{formatCount(commit.deleted_records)}</TableCell>
        <TableCell numeric>{formatCount(commit.added_data_files)}</TableCell>
        <TableCell numeric>{formatCount(commit.deleted_data_files)}</TableCell>
      </TableRow>
      {open && (
        <TableRow>
          <TableCell colSpan={7} className="bg-surface-container">
            <p className="type-code">Snapshot id: {commit.snapshot_id}</p>
            <p className="type-code">Parent id: {commit.parent_id ?? "—"}</p>
            <pre className="type-code mt-2 overflow-x-auto rounded-md bg-surface-container-dim p-2">
              {JSON.stringify(commit.summary, null, 2)}
            </pre>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

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
        <ExpandableRowsTable caption="Commits, newest first">
          <TableHeader>
            <TableRow>
              <TableHead className={STICKY_FIRST_CELL}>Committed</TableHead>
              <TableHead>Operation</TableHead>
              <TableHead>Writer</TableHead>
              <TableHead numeric>Rows added</TableHead>
              <TableHead numeric>Rows removed</TableHead>
              <TableHead numeric>Files added</TableHead>
              <TableHead numeric>Files removed</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedNewestFirst(commits.data.items).map((c) => (
              <CommitRow key={c.snapshot_id} commit={c} />
            ))}
            {commits.data.items.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-on-surface-variant">
                  No commits.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </ExpandableRowsTable>
      </Panel>
      {commits.data.truncated && (
        <p className="type-body-small mt-3 text-notice-text">Showing the newest commits only.</p>
      )}
    </>
  );
}
