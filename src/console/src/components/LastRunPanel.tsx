import type { TableMaintenanceRunApiResponse } from "@/api/types";
import { Panel } from "@/components/Panel";
import { RunStatusBadge } from "@/components/RunStatusBadge";
import { formatDuration, formatTimestamp } from "@/format";

export function LastRunPanel({ runs }: { runs: TableMaintenanceRunApiResponse[] }) {
  const last = [...runs].sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
  return (
    <Panel title="Last maintenance run">
      {last === undefined ? (
        <p className="p-4 text-[13px] text-muted-foreground">No maintenance runs yet.</p>
      ) : (
        <dl className="grid grid-cols-[max-content_1fr] items-center gap-x-4 gap-y-1.5 p-4 text-sm">
          <dt className="text-muted-foreground">Status</dt>
          <dd>
            <RunStatusBadge status={last.status} />
          </dd>
          <dt className="text-muted-foreground">Trigger</dt>
          <dd>{last.trigger}</dd>
          <dt className="text-muted-foreground">Started</dt>
          <dd className="tabular-nums">{formatTimestamp(last.created_at)}</dd>
          <dt className="text-muted-foreground">Duration</dt>
          <dd className="tabular-nums">{formatDuration(last.created_at, last.finished_at)}</dd>
        </dl>
      )}
    </Panel>
  );
}
