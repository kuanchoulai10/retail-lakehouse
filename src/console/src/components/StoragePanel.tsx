import type { TableStorageApiResponse } from "../api/types";
import { formatBytes, formatCount } from "../format";

interface Props {
  storage: TableStorageApiResponse;
}

interface ReclaimedRow {
  label: string;
  value: string;
}

const DELETED_KEYS = [
  "deleted_data_files_count",
  "deleted_manifest_files_count",
  "deleted_position_delete_files_count",
  "deleted_equality_delete_files_count",
];

function reclaimedRows(reclaimed: Record<string, number>): ReclaimedRow[] {
  const rows: ReclaimedRow[] = [];
  const rewritten = reclaimed.rewritten_data_files_count;
  if (rewritten !== undefined) {
    rows.push({
      label: "Data files rewritten",
      value: `${formatCount(rewritten)} → ${formatCount(reclaimed.added_data_files_count ?? 0)}`,
    });
  }
  const bytes = reclaimed.rewritten_bytes_count;
  if (bytes !== undefined) rows.push({ label: "Bytes rewritten", value: formatBytes(bytes) });
  const manifests = reclaimed.rewritten_manifests_count;
  if (manifests !== undefined) {
    rows.push({
      label: "Manifests rewritten",
      value: `${formatCount(manifests)} → ${formatCount(reclaimed.added_manifests_count ?? 0)}`,
    });
  }
  const expired = reclaimed.deleted_manifest_lists_count;
  if (expired !== undefined) rows.push({ label: "Snapshots expired", value: formatCount(expired) });
  if (DELETED_KEYS.some((key) => reclaimed[key] !== undefined)) {
    const total = DELETED_KEYS.reduce((sum, key) => sum + (reclaimed[key] ?? 0), 0);
    rows.push({ label: "Files deleted by expiry", value: formatCount(total) });
  }
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
