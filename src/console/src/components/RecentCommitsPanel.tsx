import type { TableCommitApiResponse } from "../api/types";
import { formatCount, formatTimestamp } from "../format";

export function RecentCommitsPanel({ commits }: { commits: TableCommitApiResponse[] }) {
  const latest = [...commits]
    .sort((a, b) => b.committed_at.localeCompare(a.committed_at))
    .slice(0, 5);
  return (
    <section className="panel" aria-label="Recent commits">
      <h2>Recent commits</h2>
      <table className="data-table">
        <thead>
          <tr>
            <th>Committed</th>
            <th>Operation</th>
            <th>Added records</th>
            <th>Added files</th>
          </tr>
        </thead>
        <tbody>
          {latest.map((commit) => (
            <tr key={commit.snapshot_id}>
              <td>{formatTimestamp(commit.committed_at)}</td>
              <td>{commit.operation ?? "—"}</td>
              <td>{formatCount(commit.added_records)}</td>
              <td>{formatCount(commit.added_data_files)}</td>
            </tr>
          ))}
          {latest.length === 0 && (
            <tr>
              <td colSpan={4} className="empty">
                No commits yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
}
