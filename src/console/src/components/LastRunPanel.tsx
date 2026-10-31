import type { TableMaintenanceRunApiResponse } from "../api/types";
import { formatDuration, formatTimestamp } from "../format";

export function LastRunPanel({ runs }: { runs: TableMaintenanceRunApiResponse[] }) {
  const last = [...runs].sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
  return (
    <section className="panel" aria-label="Last maintenance run">
      <h2>Last maintenance run</h2>
      {last === undefined ? (
        <p className="muted">No maintenance runs yet.</p>
      ) : (
        <dl className="facts">
          <dt>Status</dt>
          <dd>
            <span className={`badge badge-${last.status}`}>{last.status.toUpperCase()}</span>
          </dd>
          <dt>Trigger</dt>
          <dd>{last.trigger}</dd>
          <dt>Started</dt>
          <dd>{formatTimestamp(last.created_at)}</dd>
          <dt>Duration</dt>
          <dd>{formatDuration(last.created_at, last.finished_at)}</dd>
        </dl>
      )}
    </section>
  );
}
