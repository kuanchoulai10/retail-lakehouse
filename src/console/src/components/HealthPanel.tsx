import { useRef, useState } from "react";
import type { TableHealthApiResponse, TableHealthOperationApiResponse } from "@/api/types";
import { Panel } from "@/components/Panel";
import { RunMaintenanceDialog } from "@/components/RunMaintenanceDialog";
import { Button } from "@/components/ui/button";
import { formatTimestamp } from "@/format";
import { cn } from "@/lib/utils";

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
  const triggerRef = useRef<HTMLElement | null>(null);
  return (
    <Panel title="Health">
      {!health.scheduled && (
        <p role="status" className="border-b border-border bg-card px-4 py-2.5 text-[13px] text-muted-foreground">
          {`The scheduler skips this table: ${health.not_scheduled_reason ?? "unknown"}`}
        </p>
      )}
      <ul className="divide-y divide-border">
        {health.operations.map((line) => (
          <li key={line.operation} className="flex items-center gap-3 px-4 py-2.5 text-sm">
            <span className="min-w-44 font-mono text-[13px]">{line.operation}</span>
            <span
              className={cn(
                "flex-1 tabular-nums",
                line.verdict === "due" ? "text-warning" : "text-muted-foreground",
              )}
            >
              {lineText(line, health.scheduled)}
            </span>
            {health.scheduled && line.verdict === "due" && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={(event) => {
                  triggerRef.current = event.currentTarget;
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
      <dl className="flex items-baseline gap-4 border-t border-border px-4 py-2.5 text-[13px]">
        <dt className="text-muted-foreground">Delete files</dt>
        <dd className="tabular-nums">{`${health.position_delete_files} position, ${health.equality_delete_files} equality`}</dd>
      </dl>
      {runOperation !== null && (
        <RunMaintenanceDialog
          key={openCount}
          tableUuid={tableUuid}
          initialOperations={[runOperation]}
          open={dialogOpen}
          returnFocusTo={triggerRef}
          onClose={() => setDialogOpen(false)}
        />
      )}
    </Panel>
  );
}
