import { Banner, createDataTableColumnHelper, DataTable, Drawer, Panel, TextLink } from "@retail-lakehouse/design-system";
import { useMemo } from "react";
import { ApiError } from "@/api/apiError";
import type { TableMaintenanceRunApiResponse } from "@/api/generated/model";
import {
  useGetTableMaintenanceRun,
  useListTableMaintenanceRuns,
} from "@/api/generated/table-maintenance-runs/table-maintenance-runs";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { RunStatusBadge } from "@/components/RunStatusBadge";
import { MaintenanceRunPanel } from "@/components/tabs/MaintenanceRunPanel";
import { operationLabel } from "@/components/tabs/reconciliationText";
import { useOpenRecord } from "@/components/tabs/useOpenRecord";
import { errorMessage, formatDuration, formatTimestamp } from "@/format";
import { anyRunInFlight } from "@/lib/anyRunInFlight";
import { temporalWorkflowsUrl } from "@/lib/temporalWorkflowsUrl";

// While a run is in flight the list is read again this often, so its queued and running times keep counting.
const IN_FLIGHT_REFETCH_MS = 15_000;

const column = createDataTableColumnHelper<TableMaintenanceRunApiResponse>();

const columns = column.columns([
  column.accessor((run) => operationLabel(run.operation), { id: "operation", header: "Operation", enableSorting: false }),
  column.accessor("trigger", { header: "Trigger", enableSorting: false }),
  column.accessor("status", {
    header: "Status",
    enableSorting: false,
    cell: (info) => <RunStatusBadge status={info.getValue()} />,
  }),
  column.accessor("started_at", {
    header: "Started",
    enableSorting: false,
    cell: (info) => {
      const startedAt = info.getValue();
      return <span className="tabular-nums whitespace-nowrap">{startedAt === null ? "—" : formatTimestamp(startedAt)}</span>;
    },
  }),
  column.accessor((run) => (run.started_at === null ? "—" : formatDuration(run.started_at, run.finished_at)), {
    id: "duration",
    header: "Duration",
    enableSorting: false,
    cell: (info) => <span className="tabular-nums">{info.getValue()}</span>,
  }),
]);

// A 404 is a run that no longer exists; a 422 is an id that cannot name a run, which is what a link
// from before the mr- prefix carries. Either way the link points at nothing.
function isGone(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 404 || error.status === 422);
}

type Shown =
  | { kind: "run"; run: TableMaintenanceRunApiResponse; now: Date }
  | { kind: "loading" }
  | { kind: "message"; text: string }
  | { kind: "error"; error: unknown };

function PanelContent({ shown }: { shown: Shown }) {
  switch (shown.kind) {
    case "run":
      return <MaintenanceRunPanel run={shown.run} now={shown.now} />;
    case "loading":
      return <PanelSkeleton label="Loading run…" />;
    case "message":
      return <p className="type-body-medium text-on-surface-variant">{shown.text}</p>;
    case "error":
      return <Banner type="negative" title={`Could not load the run: ${errorMessage(shown.error)}`} />;
  }
}

// The runs of the table, newest first, one row per run. A row opens its run in a side panel beside
// the list (full width and modal on a phone), kept in the url as `?run=<id>`, the link a
// reconciliation gives to the run it started. The panel shows the listed run, so it refreshes with
// the list's in-flight polling; a run older than the runs listed is read by its id.
// The Temporal link is a plain anchor, not a router Link: the Temporal UI is another app on the
// gateway, outside the console's base path.
export function MaintenanceTab({ tableUuid }: { tableUuid: string }) {
  const runs = useListTableMaintenanceRuns(tableUuid, undefined, {
    query: { refetchInterval: (query) => (anyRunInFlight(query.state.data) ? IN_FLIGHT_REFETCH_MS : false) },
  });
  const { openId, open, close } = useOpenRecord("run");
  const listed = openId === null ? undefined : runs.data?.find((run) => run.run_id === openId);
  const notInList = openId !== null && runs.data !== undefined && listed === undefined;
  const byId = useGetTableMaintenanceRun(openId ?? "", { query: { enabled: notInList } });
  // A queued or running attempt counts up to the moment the runs were last read.
  const now = useMemo(() => new Date(runs.dataUpdatedAt), [runs.dataUpdatedAt]);
  const byIdNow = useMemo(() => new Date(byId.dataUpdatedAt), [byId.dataUpdatedAt]);

  if (runs.isPending) return <PanelSkeleton label="Loading runs…" />;
  // A failed background read keeps the runs it already has on screen; only a first read that fails replaces them.
  if (runs.isError && runs.data === undefined) {
    return <Banner type="negative" title={`Could not load maintenance runs: ${errorMessage(runs.error)}`} />;
  }

  const shown: Shown =
    listed !== undefined
      ? { kind: "run", run: listed, now }
      : byId.data !== undefined
        ? byId.data.table_uuid === tableUuid
          ? { kind: "run", run: byId.data, now: byIdNow }
          : { kind: "message", text: "This run belongs to another table" }
        : byId.isError
          ? isGone(byId.error)
            ? { kind: "message", text: "This run is no longer available" }
            : { kind: "error", error: byId.error }
          : { kind: "loading" };

  return (
    <Panel
      title="Maintenance runs"
      actions={
        <TextLink asChild className="type-body-small">
          <a href={temporalWorkflowsUrl(tableUuid)}>Running workflows in Temporal</a>
        </TextLink>
      }
    >
      {runs.isError && (
        <Banner type="information" title="Could not refresh. Times shown are from the last read." className="mb-4" />
      )}
      <DataTable
        caption="Maintenance runs, newest first"
        columns={columns}
        data={runs.data}
        getRowId={(run) => run.run_id}
        getRowLabel={(run) => `${operationLabel(run.operation)} run ${run.run_id}`}
        onOpenRow={(run) => open(run.run_id)}
        openRowId={openId}
        emptyState="No maintenance runs yet."
      />
      <Drawer
        modal={false}
        contentKey={openId ?? undefined}
        isOpen={openId !== null}
        onOpenChange={(isOpen) => {
          if (!isOpen) close();
        }}
        title={shown.kind === "run" ? operationLabel(shown.run.operation) : "Maintenance run"}
      >
        <PanelContent shown={shown} />
      </Drawer>
    </Panel>
  );
}
