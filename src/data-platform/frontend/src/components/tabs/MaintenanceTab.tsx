import { Banner, createDataTableColumnHelper, DataTable, Panel } from "@retail-lakehouse/design-system";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api/client";
import type { JsonObject, TableMaintenanceRunApiResponse } from "@/api/types";
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

function RunDetail({ run }: { run: TableMaintenanceRunApiResponse }) {
  return (
    <>
      <p className="type-body-small mb-3">
        Execution: <code className="font-mono">{run.execution_ref}</code>
      </p>
      <ul className="flex flex-col gap-3">
        {run.operations.map((op) => (
          <OperationDetail key={String(op.operation)} operation={op} />
        ))}
      </ul>
    </>
  );
}

const column = createDataTableColumnHelper<TableMaintenanceRunApiResponse>();

const columns = column.columns([
  column.accessor("trigger", { header: "Trigger", enableSorting: false }),
  column.accessor("status", {
    header: "Status",
    enableSorting: false,
    cell: (info) => <RunStatusBadge status={info.getValue()} />,
  }),
  column.accessor("created_at", {
    header: "Started",
    enableSorting: false,
    cell: (info) => <span className="tabular-nums whitespace-nowrap">{formatTimestamp(info.getValue())}</span>,
  }),
  column.accessor((run) => formatDuration(run.created_at, run.finished_at), {
    id: "duration",
    header: "Duration",
    enableSorting: false,
    cell: (info) => <span className="tabular-nums">{info.getValue()}</span>,
  }),
]);

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
      <DataTable
        caption="Maintenance runs, newest first"
        columns={columns}
        data={runs.data}
        getRowId={(run) => run.run_id}
        getRowLabel={(run) => `run ${run.run_id}`}
        renderDetail={(run) => <RunDetail run={run} />}
        emptyState="No maintenance runs yet."
      />
    </Panel>
  );
}
