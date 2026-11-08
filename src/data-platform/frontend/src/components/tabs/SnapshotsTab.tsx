import { Badge, createDataTableColumnHelper, DataTable, Panel } from "@retail-lakehouse/design-system";
import type { CatalogTableApiResponse, SnapshotApiResponse } from "@/api/catalogTypes";
import { formatTimestamp } from "@/format";

// Newest first; ids are 64-bit decimal strings, so a tie is broken with BigInt, never Number.
function newestFirst(snapshots: SnapshotApiResponse[]): SnapshotApiResponse[] {
  return [...snapshots].sort((a, b) => {
    if (a.timestamp_ms !== b.timestamp_ms) return b.timestamp_ms - a.timestamp_ms;
    const difference = BigInt(b.id) - BigInt(a.id);
    return difference > 0n ? 1 : difference < 0n ? -1 : 0;
  });
}

function SnapshotSummary({ snapshot }: { snapshot: SnapshotApiResponse }) {
  const summary = Object.entries(snapshot.summary).sort(([a], [b]) => a.localeCompare(b));
  if (summary.length === 0) return <p className="type-body-small text-on-surface-variant">No summary.</p>;
  return (
    <dl className="type-code grid grid-cols-[minmax(0,16rem)_1fr] gap-x-4 gap-y-1">
      {summary.map(([key, value]) => (
        <div key={key} className="contents">
          <dt className="text-on-surface-variant">{key}</dt>
          <dd className="break-all">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

const column = createDataTableColumnHelper<SnapshotApiResponse>();

function snapshotColumns(currentSnapshotId: string | null) {
  return column.columns([
    column.accessor("id", {
      header: "Snapshot id",
      enableSorting: false,
      cell: (info) => <span className="type-code">{info.getValue()}</span>,
    }),
    column.display({
      id: "current",
      header: () => <span className="sr-only">Current</span>,
      cell: (info) => (info.row.original.id === currentSnapshotId ? <Badge>Current</Badge> : null),
    }),
    column.accessor("parent_id", {
      header: "Parent id",
      enableSorting: false,
      cell: (info) => <span className="type-code">{info.getValue() ?? "—"}</span>,
    }),
    column.accessor("timestamp_ms", {
      header: "Committed",
      enableSorting: false,
      cell: (info) => (
        <span className="tabular-nums whitespace-nowrap">{formatTimestamp(new Date(info.getValue()).toISOString())}</span>
      ),
    }),
    column.accessor("operation", {
      header: "Operation",
      enableSorting: false,
      cell: (info) => <span className="type-code">{info.getValue() ?? "—"}</span>,
    }),
  ]);
}

export function SnapshotsTab({ table }: { table: CatalogTableApiResponse }) {
  return (
    <Panel title="Snapshots">
      <DataTable
        caption="Snapshots, newest first"
        columns={snapshotColumns(table.current_snapshot_id)}
        data={newestFirst(table.snapshots)}
        getRowId={(snapshot) => snapshot.id}
        getRowLabel={(snapshot) => `snapshot ${snapshot.id}`}
        renderDetail={(snapshot) => <SnapshotSummary snapshot={snapshot} />}
        emptyState="No snapshots."
      />
    </Panel>
  );
}
