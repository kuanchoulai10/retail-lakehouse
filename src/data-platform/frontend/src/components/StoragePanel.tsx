import type { TableStorageApiResponse, TableStorageReclaimedApiResponse } from "@/api/types";
import { Panel } from "@/components/Panel";
import { formatBytes, formatCount } from "@/format";

interface Props {
  storage: TableStorageApiResponse;
}

interface ReclaimedRow {
  label: string;
  value: string;
}

function reclaimedRows(reclaimed: TableStorageReclaimedApiResponse): ReclaimedRow[] {
  const rows: ReclaimedRow[] = [];
  if (reclaimed.rewritten_data_files > 0 || reclaimed.added_data_files > 0) {
    rows.push({
      label: "Data files rewritten",
      value: `${formatCount(reclaimed.rewritten_data_files)} → ${formatCount(reclaimed.added_data_files)}`,
    });
  }
  if (reclaimed.rewritten_bytes > 0) {
    rows.push({ label: "Bytes rewritten", value: formatBytes(reclaimed.rewritten_bytes) });
  }
  if (reclaimed.rewritten_manifests > 0 || reclaimed.added_manifests > 0) {
    rows.push({
      label: "Manifests rewritten",
      value: `${formatCount(reclaimed.rewritten_manifests)} → ${formatCount(reclaimed.added_manifests)}`,
    });
  }
  if (reclaimed.expired_snapshots > 0) {
    rows.push({ label: "Snapshots expired", value: formatCount(reclaimed.expired_snapshots) });
  }
  const deleted =
    reclaimed.deleted_data_files +
    reclaimed.deleted_manifest_files +
    reclaimed.deleted_position_delete_files +
    reclaimed.deleted_equality_delete_files;
  if (deleted > 0) rows.push({ label: "Files deleted by expiry", value: formatCount(deleted) });
  return rows;
}

export function StoragePanel({ storage }: Props) {
  const total = storage.current_bytes + storage.old_snapshot_bytes;
  const currentShare = total === 0 ? 100 : (storage.current_bytes / total) * 100;
  const rows = reclaimedRows(storage.reclaimed);
  return (
    <Panel title="Storage">
      <div className="space-y-3 p-4">
        <div className="flex h-2 overflow-hidden rounded-full bg-muted">
          <div
            role="img"
            aria-label="Current snapshot"
            className="bg-foreground"
            style={{ width: `${currentShare}%` }}
          />
          <div
            role="img"
            aria-label="Only in old snapshots"
            className="bg-muted-foreground/40"
            style={{ width: `${100 - currentShare}%` }}
          />
        </div>
        <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
          <dt className="flex items-center gap-2 text-muted-foreground">
            <span aria-hidden className="size-2 rounded-full bg-foreground" />
            Current snapshot
          </dt>
          <dd className="tabular-nums">
            <span>{formatBytes(storage.current_bytes)}</span>{" "}
            <span className="text-muted-foreground">{`${formatCount(storage.current_files)} files`}</span>
          </dd>
          <dt className="flex items-center gap-2 text-muted-foreground">
            <span aria-hidden className="size-2 rounded-full bg-muted-foreground/40" />
            Only in old snapshots
          </dt>
          <dd className="tabular-nums">
            <span>{formatBytes(storage.old_snapshot_bytes)}</span>{" "}
            <span className="text-muted-foreground">{`${formatCount(storage.old_snapshot_files)} files`}</span>
          </dd>
        </dl>
      </div>
      <div className="space-y-2 border-t border-border p-4">
        <h3 className="text-sm font-medium">{`Reclaimed in the last ${storage.window_days} days`}</h3>
        {rows.length === 0 ? (
          <p className="text-[13px] text-muted-foreground">Nothing reclaimed.</p>
        ) : (
          <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
            {rows.map((row) => (
              <div key={row.label} className="contents">
                <dt className="text-muted-foreground">{row.label}</dt>
                <dd className="tabular-nums">{row.value}</dd>
              </div>
            ))}
          </dl>
        )}
        {storage.attempts_without_metrics > 0 && (
          <p className="text-[13px] text-muted-foreground">
            {`${storage.attempts_without_metrics} attempts in this window reported no metrics and add nothing above.`}
          </p>
        )}
      </div>
    </Panel>
  );
}
