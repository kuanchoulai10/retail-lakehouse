import { Banner, createDataTableColumnHelper, DataTable, Panel } from "@retail-lakehouse/design-system";
import { useSearchParams } from "react-router";
import type { TableMaintenanceRunApiResponse } from "@/api/generated/model";
import { useListTableMaintenanceRuns } from "@/api/generated/table-maintenance-runs/table-maintenance-runs";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { RunStatusBadge } from "@/components/RunStatusBadge";
import { errorMessage, formatDuration, formatTimestamp } from "@/format";

function OperationDetail({ operation }: { operation: Record<string, unknown> }) {
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

// `?run=<id>` (a reconciliation's link to the run it started) opens that run. The DataTable reads
// it once on mount, so it mounts only after the runs load and is keyed on the id: a new id
// (back/forward) remounts it with the new run open.
// The check runs against the latest runs the API returns; an older run counts as gone.
export function MaintenanceTab({ tableUuid }: { tableUuid: string }) {
  const runs = useListTableMaintenanceRuns(tableUuid);
  const [searchParams] = useSearchParams();
  const linkedRunId = searchParams.get("run");

  if (runs.isPending) return <PanelSkeleton label="Loading runs…" />;
  if (runs.isError) {
    return <Banner type="negative" title={`Could not load maintenance runs: ${errorMessage(runs.error)}`} />;
  }
  const missing = linkedRunId !== null && !runs.data.some((run) => run.run_id === linkedRunId);
  return (
    <Panel title="Maintenance runs">
      {missing && <Banner type="information" title="This run is no longer available" className="mb-4" />}
      <DataTable
        key={linkedRunId ?? ""}
        caption="Maintenance runs, newest first"
        columns={columns}
        data={runs.data}
        getRowId={(run) => run.run_id}
        getRowLabel={(run) => `run ${run.run_id}`}
        {...(linkedRunId === null ? {} : { initialExpandedRowIds: [linkedRunId] })}
        renderDetail={(run) => <RunDetail run={run} />}
        emptyState="No maintenance runs yet."
      />
    </Panel>
  );
}
