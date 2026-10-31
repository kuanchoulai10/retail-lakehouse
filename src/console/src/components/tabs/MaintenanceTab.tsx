import { useQuery } from "@tanstack/react-query";
import { ChevronRight } from "lucide-react";
import { useState } from "react";
import { apiGet } from "@/api/client";
import type { JsonObject, TableMaintenanceRunApiResponse } from "@/api/types";
import { Panel } from "@/components/Panel";
import { RunStatusBadge } from "@/components/RunStatusBadge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { errorMessage, formatDuration, formatTimestamp } from "@/format";
import { cn } from "@/lib/utils";

function OperationDetail({ operation }: { operation: JsonObject }) {
  const attempts = Number(operation.attempts ?? 0);
  const metrics = Object.entries((operation.metrics as Record<string, number> | undefined) ?? {});
  const error = operation.error as string | null | undefined;
  return (
    <li className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <strong className="font-mono text-[13px] font-medium">{String(operation.operation)}</strong>
        <RunStatusBadge status={String(operation.status)} />
        <span className="text-[13px] text-muted-foreground">{`${attempts} ${attempts === 1 ? "attempt" : "attempts"}`}</span>
      </div>
      {metrics.length > 0 && (
        <ul className="font-mono text-[13px] text-muted-foreground">
          {metrics.map(([name, value]) => (
            <li key={name}>{`${name}: ${value}`}</li>
          ))}
        </ul>
      )}
      {error && <p className="text-[13px] text-destructive">{error}</p>}
    </li>
  );
}

function RunRow({ run }: { run: TableMaintenanceRunApiResponse }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <TableRow className="cursor-pointer" onClick={() => setOpen(!open)}>
        <TableCell>
          <button
            type="button"
            aria-expanded={open}
            aria-label={`${open ? "Collapse" : "Expand"} run ${run.run_id}`}
            className="flex items-center gap-1"
          >
            <ChevronRight className={cn("size-4 text-muted-foreground", open && "rotate-90")} />
            <span>{run.trigger}</span>
          </button>
        </TableCell>
        <TableCell>
          <RunStatusBadge status={run.status} />
        </TableCell>
        <TableCell className="tabular-nums">{formatTimestamp(run.created_at)}</TableCell>
        <TableCell className="tabular-nums">
          {formatDuration(run.created_at, run.finished_at)}
        </TableCell>
      </TableRow>
      {open && (
        <TableRow>
          <TableCell colSpan={4} className="bg-card whitespace-normal">
            <p className="mb-3 text-[13px]">
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

  if (runs.isPending) return <p className="text-sm text-muted-foreground">Loading runs…</p>;
  if (runs.isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Could not load maintenance runs: {errorMessage(runs.error)}
      </p>
    );
  }
  return (
    <Panel title="Maintenance runs">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Trigger</TableHead>
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
              <TableCell colSpan={4} className="text-center text-muted-foreground">
                No maintenance runs yet.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </Panel>
  );
}
