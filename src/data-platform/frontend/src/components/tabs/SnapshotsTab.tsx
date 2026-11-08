import {
  Badge,
  Panel,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@retail-lakehouse/design-system";
import { useState } from "react";
import type { CatalogTableApiResponse, SnapshotApiResponse } from "@/api/catalogTypes";
import { ExpandableRowsTable, STICKY_FIRST_CELL } from "@/components/ExpandableRowsTable";
import { ExpandToggle } from "@/components/ExpandToggle";
import { formatTimestamp } from "@/format";

// Newest first; ids are 64-bit decimal strings, so a tie is broken with BigInt, never Number.
function newestFirst(snapshots: SnapshotApiResponse[]): SnapshotApiResponse[] {
  return [...snapshots].sort((a, b) => {
    if (a.timestamp_ms !== b.timestamp_ms) return b.timestamp_ms - a.timestamp_ms;
    const difference = BigInt(b.id) - BigInt(a.id);
    return difference > 0n ? 1 : difference < 0n ? -1 : 0;
  });
}

function SnapshotRow({ snapshot, current }: { snapshot: SnapshotApiResponse; current: boolean }) {
  const [open, setOpen] = useState(false);
  const summary = Object.entries(snapshot.summary).sort(([a], [b]) => a.localeCompare(b));
  return (
    <>
      <TableRow className="cursor-pointer" onClick={() => setOpen(!open)}>
        <TableCell className={STICKY_FIRST_CELL}>
          <ExpandToggle open={open} label={`${open ? "Collapse" : "Expand"} snapshot ${snapshot.id}`}>
            <span className="type-code">{snapshot.id}</span>
          </ExpandToggle>
        </TableCell>
        <TableCell>{current && <Badge>Current</Badge>}</TableCell>
        <TableCell className="type-code">{snapshot.parent_id ?? "—"}</TableCell>
        <TableCell className="tabular-nums whitespace-nowrap">
          {formatTimestamp(new Date(snapshot.timestamp_ms).toISOString())}
        </TableCell>
        <TableCell className="type-code">{snapshot.operation ?? "—"}</TableCell>
      </TableRow>
      {open && (
        <TableRow>
          <TableCell colSpan={5} className="bg-surface-container">
            {summary.length === 0 ? (
              <p className="type-body-small text-on-surface-variant">No summary.</p>
            ) : (
              <dl className="type-code grid grid-cols-[minmax(0,16rem)_1fr] gap-x-4 gap-y-1">
                {summary.map(([key, value]) => (
                  <div key={key} className="contents">
                    <dt className="text-on-surface-variant">{key}</dt>
                    <dd className="break-all">{value}</dd>
                  </div>
                ))}
              </dl>
            )}
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

export function SnapshotsTab({ table }: { table: CatalogTableApiResponse }) {
  const snapshots = newestFirst(table.snapshots);
  return (
    <Panel title="Snapshots">
      <ExpandableRowsTable caption="Snapshots, newest first">
        <TableHeader>
          <TableRow>
            <TableHead className={STICKY_FIRST_CELL}>Snapshot id</TableHead>
            <TableHead>
              <span className="sr-only">Current</span>
            </TableHead>
            <TableHead>Parent id</TableHead>
            <TableHead>Committed</TableHead>
            <TableHead>Operation</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {snapshots.map((snapshot) => (
            <SnapshotRow key={snapshot.id} snapshot={snapshot} current={snapshot.id === table.current_snapshot_id} />
          ))}
          {snapshots.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-on-surface-variant">
                No snapshots.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </ExpandableRowsTable>
    </Panel>
  );
}
