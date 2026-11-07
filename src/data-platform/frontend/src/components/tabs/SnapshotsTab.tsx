import { ChevronRight } from "lucide-react";
import { useState } from "react";
import type { CatalogTableApiResponse, SnapshotApiResponse } from "@/api/catalogTypes";
import { Panel } from "@/components/Panel";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatTimestamp } from "@/format";
import { cn } from "@/lib/utils";

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
        <TableCell>
          <button
            type="button"
            aria-expanded={open}
            aria-label={`${open ? "Collapse" : "Expand"} snapshot ${snapshot.id}`}
            className="flex items-center gap-1"
          >
            <ChevronRight className={cn("size-4 text-muted-foreground", open && "rotate-90")} />
            <span className="font-mono text-[13px]">{snapshot.id}</span>
          </button>
        </TableCell>
        <TableCell>{current && <Badge variant="outline">Current</Badge>}</TableCell>
        <TableCell className="font-mono text-[13px]">{snapshot.parent_id ?? "—"}</TableCell>
        <TableCell className="tabular-nums">{formatTimestamp(new Date(snapshot.timestamp_ms).toISOString())}</TableCell>
        <TableCell className="font-mono text-[13px]">{snapshot.operation ?? "—"}</TableCell>
      </TableRow>
      {open && (
        <TableRow>
          <TableCell colSpan={5} className="bg-card whitespace-normal">
            {summary.length === 0 ? (
              <p className="text-[13px] text-muted-foreground">No summary.</p>
            ) : (
              <dl className="grid grid-cols-[minmax(0,16rem)_1fr] gap-x-4 gap-y-1 font-mono text-[13px]">
                {summary.map(([key, value]) => (
                  <div key={key} className="contents">
                    <dt className="text-muted-foreground">{key}</dt>
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
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Snapshot id</TableHead>
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
              <TableCell colSpan={5} className="text-center text-muted-foreground">
                No snapshots.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </Panel>
  );
}
