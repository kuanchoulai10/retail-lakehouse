import { Panel } from "@retail-lakehouse/design-system";
import type { TableMaintenanceRunApiResponse } from "@/api/types";
import { RunStatusBadge } from "@/components/RunStatusBadge";
import { formatDuration, formatTimestamp } from "@/format";

export function LastRunPanel({ runs }: { runs: TableMaintenanceRunApiResponse[] }) {
  const last = [...runs].sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
  return (
    <Panel title="Last maintenance run">
      {last === undefined ? (
        <p className="type-body-small text-on-surface-variant">No maintenance runs yet.</p>
      ) : (
        <dl className="grid grid-cols-[max-content_1fr] items-center gap-x-4 gap-y-1.5">
          <dt className="text-on-surface-variant">Status</dt>
          <dd>
            <RunStatusBadge status={last.status} />
          </dd>
          <dt className="text-on-surface-variant">Trigger</dt>
          <dd>{last.trigger}</dd>
          <dt className="text-on-surface-variant">Started</dt>
          <dd className="tabular-nums">{formatTimestamp(last.created_at)}</dd>
          <dt className="text-on-surface-variant">Duration</dt>
          <dd className="tabular-nums">{formatDuration(last.created_at, last.finished_at)}</dd>
        </dl>
      )}
    </Panel>
  );
}
