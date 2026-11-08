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
import type { JsonObject, TableMaintenanceRunApiResponse } from "@/api/types";
import { ExpandableRowsTable, STICKY_FIRST_CELL } from "@/components/ExpandableRowsTable";
import { ExpandToggle } from "@/components/ExpandToggle";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { RunStatusBadge } from "@/components/RunStatusBadge";
import { errorMessage, formatDuration, formatTimestamp } from "@/format";

function OperationDetail({ operation }: { operation: JsonObject }) {
  const attempts = Number(operation.attempts ?? 0);
  const metrics = Object.entries((operation.metrics as Record<string, number> | undefined) ?? {});
  const error = operation.error as string | null | undefined;
  return (
    <li className="flex flex-col gap-1">
      <div className="flex flex-wrap items-center gap-2">
        <strong className="type-code font-medium">{String(operation.operation)}</strong>
        <RunStatusBadge status={String(operation.status)} />
        <span className="type-body-small text-on-surface-variant">{`${attempts} ${attempts === 1 ? "attempt" : "attempts"}`}</span>
      </div>
      {metrics.length > 0 && (
        <ul className="type-code text-on-surface-variant">
          {metrics.map(([name, value]) => (
            <li key={name}>{`${name}: ${value}`}</li>
          ))}
        </ul>
      )}
      {error && <p className="type-body-small text-negative-text">{error}</p>}
    </li>
  );
}

function RunRow({ run }: { run: TableMaintenanceRunApiResponse }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <TableRow className="cursor-pointer" onClick={() => setOpen(!open)}>
        <TableCell className={STICKY_FIRST_CELL}>
          <ExpandToggle open={open} label={`${open ? "Collapse" : "Expand"} run ${run.run_id}`}>
            <span>{run.trigger}</span>
          </ExpandToggle>
        </TableCell>
        <TableCell>
          <RunStatusBadge status={run.status} />
        </TableCell>
        <TableCell className="tabular-nums whitespace-nowrap">{formatTimestamp(run.created_at)}</TableCell>
        <TableCell className="tabular-nums">{formatDuration(run.created_at, run.finished_at)}</TableCell>
      </TableRow>
      {open && (
        <TableRow>
          <TableCell colSpan={4} className="bg-surface-container">
            <p className="type-body-small mb-3">
              Execution: <code className="font-mono">{run.execution_ref}</code>
            </p>
            <ul className="flex flex-col gap-3">
              {run.operations.map((op) => (
                <OperationDetail key={String(op.operation)} operation={op} />
              ))}
            </ul>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

export function MaintenanceTab({ tableUuid }: { tableUuid: string }) {
  const runs = useQuery({
    queryKey: ["runs", tableUuid],
    queryFn: () =>
      apiGet<TableMaintenanceRunApiResponse[]>(`/v1/tables/${tableUuid}/table-maintenance-runs`),
  });

  if (runs.isPending) return <PanelSkeleton label="Loading runs…" />;
  if (runs.isError) {
    return <Banner type="negative" title={`Could not load maintenance runs: ${errorMessage(runs.error)}`} />;
  }
  return (
    <Panel title="Maintenance runs">
      <ExpandableRowsTable caption="Maintenance runs, newest first">
        <TableHeader>
          <TableRow>
            <TableHead className={STICKY_FIRST_CELL}>Trigger</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Started</TableHead>
            <TableHead>Duration</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {runs.data.map((run) => (
            <RunRow key={run.run_id} run={run} />
          ))}
          {runs.data.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-on-surface-variant">
                No maintenance runs yet.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </ExpandableRowsTable>
    </Panel>
  );
}
