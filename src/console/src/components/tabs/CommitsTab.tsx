import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { apiGet } from "../../api/client";
import type { TableCommitApiResponse, TableCommitsApiResponse } from "../../api/types";
import { errorMessage, formatCount, formatTimestamp } from "../../format";
import { writerLabel } from "../../writerLabel";

function sortedNewestFirst(items: TableCommitApiResponse[]): TableCommitApiResponse[] {
  return [...items].sort((a, b) => b.committed_at.localeCompare(a.committed_at));
}

function CommitRow({ commit }: { commit: TableCommitApiResponse }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr data-testid="commit-row" className="clickable" onClick={() => setOpen(!open)}>
        <td>{formatTimestamp(commit.committed_at)}</td>
        <td>{commit.operation ?? "—"}</td>
        <td>{writerLabel(commit.writer)}</td>
        <td>{formatCount(commit.added_records)}</td>
        <td>{formatCount(commit.deleted_records)}</td>
        <td>{formatCount(commit.added_data_files)}</td>
        <td>{formatCount(commit.deleted_data_files)}</td>
      </tr>
      {open && (
        <tr>
          <td colSpan={7}>
            <p>Snapshot id: {commit.snapshot_id}</p>
            <p>Parent id: {commit.parent_id ?? "—"}</p>
            <pre>{JSON.stringify(commit.summary, null, 2)}</pre>
          </td>
        </tr>
      )}
    </>
  );
}

export function CommitsTab({ tableUuid }: { tableUuid: string }) {
  const commits = useQuery({
    queryKey: ["commits", tableUuid],
    queryFn: () => apiGet<TableCommitsApiResponse>(`/v1/tables/${tableUuid}/commits`),
  });

  if (commits.isPending) return <p>Loading commits…</p>;
  if (commits.isError) {
    return (
      <p role="alert" className="error">
        Could not load commits: {errorMessage(commits.error)}
      </p>
    );
  }
  return (
    <>
      <table className="data-table">
        <thead>
          <tr>
            <th>Committed</th>
            <th>Operation</th>
            <th>Writer</th>
            <th>Rows added</th>
            <th>Rows removed</th>
            <th>Files added</th>
            <th>Files removed</th>
          </tr>
        </thead>
        <tbody>
          {sortedNewestFirst(commits.data.items).map((c) => (
            <CommitRow key={c.snapshot_id} commit={c} />
          ))}
          {commits.data.items.length === 0 && (
            <tr>
              <td colSpan={7} className="empty">
                No commits.
              </td>
            </tr>
          )}
        </tbody>
      </table>
      {commits.data.truncated && <p className="muted">Showing the newest commits only.</p>}
    </>
  );
}
