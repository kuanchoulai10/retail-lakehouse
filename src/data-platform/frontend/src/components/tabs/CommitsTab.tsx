import { PanelSkeleton } from "@/components/PanelSkeleton";
import { useQuery } from "@tanstack/react-query";
import { ChevronRight } from "lucide-react";
import { useState } from "react";
import { apiGet } from "@/api/client";
import type { TableCommitApiResponse, TableCommitsApiResponse } from "@/api/types";
import { Panel } from "@/components/Panel";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { errorMessage, formatCount, formatTimestamp } from "@/format";
import { cn } from "@/lib/utils";
import { writerLabel } from "@/writerLabel";

function sortedNewestFirst(items: TableCommitApiResponse[]): TableCommitApiResponse[] {
  return [...items].sort((a, b) => b.committed_at.localeCompare(a.committed_at));
}

function CommitRow({ commit }: { commit: TableCommitApiResponse }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <TableRow data-testid="commit-row" className="cursor-pointer" onClick={() => setOpen(!open)}>
        <TableCell>
          <button
            type="button"
            aria-expanded={open}
            aria-label={`${open ? "Collapse" : "Expand"} commit ${commit.snapshot_id}`}
            className="flex items-center gap-1"
          >
            <ChevronRight className={cn("size-4 text-muted-foreground", open && "rotate-90")} />
            <span className="tabular-nums">{formatTimestamp(commit.committed_at)}</span>
          </button>
        </TableCell>
        <TableCell className="font-mono">{commit.operation ?? "—"}</TableCell>
        <TableCell>{writerLabel(commit.writer)}</TableCell>
        <TableCell className="text-right tabular-nums">{formatCount(commit.added_records)}</TableCell>
        <TableCell className="text-right tabular-nums">{formatCount(commit.deleted_records)}</TableCell>
        <TableCell className="text-right tabular-nums">{formatCount(commit.added_data_files)}</TableCell>
        <TableCell className="text-right tabular-nums">{formatCount(commit.deleted_data_files)}</TableCell>
      </TableRow>
      {open && (
        <TableRow>
          <TableCell colSpan={7} className="bg-card whitespace-normal">
            <p className="font-mono text-[13px]">Snapshot id: {commit.snapshot_id}</p>
            <p className="font-mono text-[13px]">Parent id: {commit.parent_id ?? "—"}</p>
            <pre className="mt-2 overflow-x-auto rounded-md bg-muted p-2 font-mono text-[13px]">
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
    return (
      <p role="alert" className="text-sm text-destructive">
        Could not load commits: {errorMessage(commits.error)}
      </p>
    );
  }
  return (
    <>
      <Panel title="Commits">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Committed</TableHead>
              <TableHead>Operation</TableHead>
              <TableHead>Writer</TableHead>
              <TableHead className="text-right">Rows added</TableHead>
              <TableHead className="text-right">Rows removed</TableHead>
              <TableHead className="text-right">Files added</TableHead>
              <TableHead className="text-right">Files removed</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedNewestFirst(commits.data.items).map((c) => (
              <CommitRow key={c.snapshot_id} commit={c} />
            ))}
            {commits.data.items.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground">
                  No commits.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Panel>
      {commits.data.truncated && (
        <p className="mt-3 text-[13px] text-warning">Showing the newest commits only.</p>
      )}
    </>
  );
}
