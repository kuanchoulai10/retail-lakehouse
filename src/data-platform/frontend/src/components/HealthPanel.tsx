import { Banner, Button, cn, Divider, Panel } from "@retail-lakehouse/design-system";
import { useState } from "react";
import type { TableHealthApiResponse, TableHealthOperationApiResponse } from "@/api/types";
import { RunMaintenanceDialog } from "@/components/RunMaintenanceDialog";
import { formatTimestamp } from "@/format";

function measurement(line: TableHealthOperationApiResponse): string {
  const { measured, threshold } = line;
  if (measured === null) return line.verdict === "due" ? "due" : "not due";
  const suffix = threshold === null ? "" : `, threshold ${threshold}`;
  switch (line.operation) {
    case "rewrite_data_files": {
      const partitions =
        line.qualifying_partitions === null ? "" : ` in ${line.qualifying_partitions} ${line.qualifying_partitions === 1 ? "partition" : "partitions"}`;
      return `${measured} reducible files${partitions}${suffix}`;
    }
    case "rewrite_manifests":
      return `${measured} small manifests${suffix}`;
    case "expire_snapshots":
      return `${measured} snapshots past retention${suffix}`;
    default:
      return `${measured}${suffix}`;
  }
}

function lineText(line: TableHealthOperationApiResponse, scheduled: boolean): string {
  switch (line.verdict) {
    case "disabled":
      return "disabled";
    case "cooldown":
      return line.next_eligible_at === null
        ? "in cooldown"
        : `in cooldown until ${formatTimestamp(line.next_eligible_at)}`;
    case "due":
      return scheduled ? measurement(line) : `${measurement(line)} (would be due when resumed)`;
    case "not_due":
      return line.measured === null ? measurement(line) : `${measurement(line)} (not due)`;
    default:
      return `${line.verdict}: ${measurement(line)}`;
  }
}

interface Props {
  tableUuid: string;
  health: TableHealthApiResponse;
}

export function HealthPanel({ tableUuid, health }: Props) {
  const [runOperation, setRunOperation] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [openCount, setOpenCount] = useState(0);
  return (
    <Panel title="Health">
      {!health.scheduled && (
        <Banner
          type="information"
          title={`The scheduler skips this table: ${health.not_scheduled_reason ?? "unknown"}`}
          className="mb-3"
        />
      )}
      <ul className="divide-y divide-outline-dim">
        {health.operations.map((line) => (
          <li key={line.operation} className="flex min-h-row flex-wrap items-center gap-x-3 gap-y-1 py-1">
            <span className="type-code min-w-44">{line.operation}</span>
            <span
              className={cn(
                "flex-1 tabular-nums",
                line.verdict === "due" ? "text-notice-text" : "text-on-surface-variant",
              )}
            >
              {lineText(line, health.scheduled)}
            </span>
            {health.scheduled && line.verdict === "due" && (
              <Button
                type="button"
                styleType="outlined"
                size="small"
                onClick={() => {
                  setRunOperation(line.operation);
                  setOpenCount((count) => count + 1);
                  setDialogOpen(true);
                }}
              >
                Run now
              </Button>
            )}
          </li>
        ))}
      </ul>
      <Divider className="my-2" />
      <dl className="type-body-small flex items-baseline gap-4">
        <dt className="text-on-surface-variant">Delete files</dt>
        <dd className="tabular-nums">{`${health.position_delete_files} position, ${health.equality_delete_files} equality`}</dd>
      </dl>
      {runOperation !== null && (
        <RunMaintenanceDialog
          key={openCount}
          tableUuid={tableUuid}
          initialOperations={[runOperation]}
          open={dialogOpen}
          onClose={() => setDialogOpen(false)}
        />
      )}
    </Panel>
  );
}
