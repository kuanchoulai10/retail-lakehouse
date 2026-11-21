import { Banner, createDataTableColumnHelper, DataTable, Panel, TextLink } from "@retail-lakehouse/design-system";
import { useMemo } from "react";
import { useSearchParams } from "react-router";
import type {
  TableMaintenanceRunApiResponse,
  TableMaintenanceRunAttemptApiResponse,
  TableMaintenanceRunOperationApiResponse,
} from "@/api/generated/model";
import { useListTableMaintenanceRuns } from "@/api/generated/table-maintenance-runs/table-maintenance-runs";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { RunStatusBadge } from "@/components/RunStatusBadge";
import { errorMessage, formatDuration, formatTimestamp } from "@/format";
import { anyRunInFlight } from "@/lib/anyRunInFlight";
import { compactionScopeText } from "@/lib/compactionScopeText";
import { eventLogText, failureClassText, nextStepText, queueWaitText, runTimeText } from "@/lib/attemptText";
import { temporalWorkflowsUrl } from "@/lib/temporalWorkflowsUrl";

// While a run is in flight the list is read again this often, so its queued and running times keep counting.
const IN_FLIGHT_REFETCH_MS = 15_000;

const attemptColumn = createDataTableColumnHelper<TableMaintenanceRunAttemptApiResponse>();

// The times of a queued or running attempt count up to `now`, so the columns are made for one.
function attemptColumnsAt(now: Date) {
  return attemptColumn.columns([
    attemptColumn.accessor("attempt", {
      header: "Attempt",
      enableSorting: false,
      cell: (info) => <span className="tabular-nums">{info.getValue()}</span>,
    }),
    attemptColumn.accessor((attempt) => attempt.size ?? "", {
      id: "size",
      header: "Size",
      enableSorting: false,
      cell: (info) => <span className="font-mono">{info.getValue()}</span>,
    }),
    attemptColumn.accessor("status", {
      header: "Result",
      enableSorting: false,
      cell: (info) => <RunStatusBadge status={info.getValue()} />,
    }),
    attemptColumn.accessor((attempt) => queueWaitText(attempt, now), {
      id: "queued",
      header: "Queued",
      enableSorting: false,
      cell: (info) => <span className="tabular-nums">{info.getValue()}</span>,
    }),
    attemptColumn.accessor((attempt) => runTimeText(attempt, now), {
      id: "ran",
      header: "Ran",
      enableSorting: false,
      cell: (info) => <span className="tabular-nums">{info.getValue()}</span>,
    }),
    attemptColumn.accessor((attempt) => failureClassText(attempt.failure_class), {
      id: "reason",
      header: "Reason",
      enableSorting: false,
    }),
    attemptColumn.accessor((attempt) => eventLogText(attempt.event_log_finished), {
      id: "event_log",
      header: "Event log",
      enableSorting: false,
    }),
    attemptColumn.accessor((attempt) => nextStepText(attempt.next_step, attempt.next_size), {
      id: "next",
      header: "Next",
      enableSorting: false,
    }),
  ]);
}

// Each attempt of the operation: the size it ran at, how long it queued and ran, why it failed,
// whether its Spark event log finished and what the platform did next. A run from before attempt
// history keeps only the count. A compaction also says its scope: the whole table, or the partitions
// over the target, each spec's where clause listed.
function OperationDetail({ operation, now }: { operation: TableMaintenanceRunOperationApiResponse; now: Date }) {
  const attemptColumns = useMemo(() => attemptColumnsAt(now), [now]);
  const attempts = operation.attempts;
  const metrics = Object.entries(operation.metrics);
  const error = operation.error;
  const scope = compactionScopeText(operation);
  return (
    <li className="flex flex-col gap-1">
      <div className="flex flex-wrap items-center gap-2">
        <strong className="type-code font-medium">{operation.operation}</strong>
        <RunStatusBadge status={operation.status} />
        <span className="type-body-small text-on-surface-variant">{`${attempts} ${attempts === 1 ? "attempt" : "attempts"}`}</span>
      </div>
      {scope && (
        <>
          <p className="type-body-small">{`Scope: ${scope.summary}`}</p>
          {scope.wheres.length > 0 && (
            <ul className="type-code text-on-surface-variant">
              {scope.wheres.map(({ specId, where }) => (
                <li key={specId} className="break-all">{`spec ${specId}: ${where}`}</li>
              ))}
            </ul>
          )}
        </>
      )}
      {operation.attempt_history.length > 0 && (
        <DataTable
          caption={`Attempts of ${operation.operation}`}
          columns={attemptColumns}
          data={operation.attempt_history}
          getRowId={(attempt) => String(attempt.attempt)}
        />
      )}
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

function RunDetail({ run, now }: { run: TableMaintenanceRunApiResponse; now: Date }) {
  return (
    <>
      <p className="type-body-small mb-3">
        Execution: <code className="font-mono">{run.execution_ref}</code>
      </p>
      <ul className="flex flex-col gap-3">
        {run.operations.map((op) => (
          <OperationDetail key={op.operation} operation={op} now={now} />
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
// The Temporal link is a plain anchor, not a router Link: the Temporal UI is another app on the
// gateway, outside the console's base path.
export function MaintenanceTab({ tableUuid }: { tableUuid: string }) {
  const runs = useListTableMaintenanceRuns(tableUuid, undefined, {
    query: { refetchInterval: (query) => (anyRunInFlight(query.state.data) ? IN_FLIGHT_REFETCH_MS : false) },
  });
  const [searchParams] = useSearchParams();
  const linkedRunId = searchParams.get("run");
  // A queued or running attempt counts up to the moment the runs were last read.
  const now = useMemo(() => new Date(runs.dataUpdatedAt), [runs.dataUpdatedAt]);

  if (runs.isPending) return <PanelSkeleton label="Loading runs…" />;
  // A failed background read keeps the runs it already has on screen; only a first read that fails replaces them.
  if (runs.isError && runs.data === undefined) {
    return <Banner type="negative" title={`Could not load maintenance runs: ${errorMessage(runs.error)}`} />;
  }
  const missing = linkedRunId !== null && !runs.data.some((run) => run.run_id === linkedRunId);
  return (
    <Panel
      title="Maintenance runs"
      actions={
        <TextLink asChild className="type-body-small">
          <a href={temporalWorkflowsUrl(tableUuid)}>Running workflows in Temporal</a>
        </TextLink>
      }
    >
      {missing && <Banner type="information" title="This run is no longer available" className="mb-4" />}
      {runs.isError && (
        <Banner type="information" title="Could not refresh. Times shown are from the last read." className="mb-4" />
      )}
      <DataTable
        key={linkedRunId ?? ""}
        caption="Maintenance runs, newest first"
        columns={columns}
        data={runs.data}
        getRowId={(run) => run.run_id}
        getRowLabel={(run) => `run ${run.run_id}`}
        {...(linkedRunId === null ? {} : { initialExpandedRowIds: [linkedRunId] })}
        renderDetail={(run) => <RunDetail run={run} now={now} />}
        emptyState="No maintenance runs yet."
      />
    </Panel>
  );
}
