import type { TableStorageApiResponse, TableStorageReclaimedApiResponse } from "../api/types";
import { formatBytes, formatCount } from "../format";

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
    <section className="panel" aria-label="Storage">
      <h2>Storage</h2>
      <div
        className="storage-bar"
        role="img"
        aria-label="Current snapshot bytes versus bytes only old snapshots reference"
      >
        <div className="storage-current" style={{ width: `${currentShare}%` }} />
        <div className="storage-old" style={{ width: `${100 - currentShare}%` }} />
      </div>
      <dl className="facts">
        <dt>Current snapshot</dt>
        <dd>
          <span>{formatBytes(storage.current_bytes)}</span>{" "}
          <span className="muted">{`${formatCount(storage.current_files)} files`}</span>
        </dd>
        <dt>Only in old snapshots</dt>
        <dd>
          <span>{formatBytes(storage.old_snapshot_bytes)}</span>{" "}
          <span className="muted">{`${formatCount(storage.old_snapshot_files)} files`}</span>
        </dd>
      </dl>
      <h3>{`Reclaimed in the last ${storage.window_days} days`}</h3>
      {rows.length === 0 ? (
        <p className="muted">Nothing reclaimed.</p>
      ) : (
        <dl className="facts">
          {rows.map((row) => (
            <div key={row.label} className="fact-row">
              <dt>{row.label}</dt>
              <dd>{row.value}</dd>
            </div>
          ))}
        </dl>
      )}
      {storage.attempts_without_metrics > 0 && (
        <p className="muted">
          {`${storage.attempts_without_metrics} attempts in this window reported no metrics and add nothing above.`}
        </p>
      )}
    </section>
  );
}
