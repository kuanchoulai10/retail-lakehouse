import { Divider, Panel } from "@retail-lakehouse/design-system";
import type { TableStorageApiResponse, TableStorageApiResponseReclaimed } from "@/api/generated/model";
import { formatBytes, formatCount } from "@/format";

interface Props {
  storage: TableStorageApiResponse;
}

interface ReclaimedRow {
  label: string;
  value: string;
}

// The API types the reclaimed counters as an open map of numbers; a counter it leaves out is 0.
function counters(map: TableStorageApiResponseReclaimed) {
  const count = (key: string) => map[key] ?? 0;
  return {
    rewritten_data_files: count("rewritten_data_files"),
    added_data_files: count("added_data_files"),
    rewritten_bytes: count("rewritten_bytes"),
    rewritten_manifests: count("rewritten_manifests"),
    added_manifests: count("added_manifests"),
    expired_snapshots: count("expired_snapshots"),
    deleted_data_files: count("deleted_data_files"),
    deleted_manifest_files: count("deleted_manifest_files"),
    deleted_position_delete_files: count("deleted_position_delete_files"),
    deleted_equality_delete_files: count("deleted_equality_delete_files"),
  };
}

function reclaimedRows(map: TableStorageApiResponseReclaimed): ReclaimedRow[] {
  const reclaimed = counters(map);
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
      <div className="space-y-3">
        <div className="flex h-2 overflow-hidden rounded-full bg-surface-container-dim">
          <div
            role="img"
            aria-label="Current snapshot"
            className="bg-chart-1"
            style={{ width: `${currentShare}%` }}
          />
          <div
            role="img"
            aria-label="Only in old snapshots"
            className="bg-chart-5"
            style={{ width: `${100 - currentShare}%` }}
          />
        </div>
        <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1">
          <dt className="flex items-center gap-2 text-on-surface-variant">
            <span aria-hidden className="size-2 rounded-full bg-chart-1" />
            Current snapshot
          </dt>
          <dd className="tabular-nums">
            <span>{formatBytes(storage.current_bytes)}</span>{" "}
            <span className="text-on-surface-variant">{`${formatCount(storage.current_files)} files`}</span>
          </dd>
          <dt className="flex items-center gap-2 text-on-surface-variant">
            <span aria-hidden className="size-2 rounded-full bg-chart-5" />
            Only in old snapshots
          </dt>
          <dd className="tabular-nums">
            <span>{formatBytes(storage.old_snapshot_bytes)}</span>{" "}
            <span className="text-on-surface-variant">{`${formatCount(storage.old_snapshot_files)} files`}</span>
          </dd>
        </dl>
      </div>
      <Divider className="my-4" />
      <div className="space-y-2">
        <h3 className="type-title-small">{`Reclaimed in the last ${storage.window_days} days`}</h3>
        {rows.length === 0 ? (
          <p className="type-body-small text-on-surface-variant">Nothing reclaimed.</p>
        ) : (
          <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1">
            {rows.map((row) => (
              <div key={row.label} className="contents">
                <dt className="text-on-surface-variant">{row.label}</dt>
                <dd className="tabular-nums">{row.value}</dd>
              </div>
            ))}
          </dl>
        )}
        {storage.attempts_without_metrics > 0 && (
          <p className="type-body-small text-on-surface-variant">
            {`${storage.attempts_without_metrics} attempts in this window reported no metrics and add nothing above.`}
          </p>
        )}
      </div>
    </Panel>
  );
}
