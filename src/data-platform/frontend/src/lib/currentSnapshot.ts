import type { CatalogTableApiResponse, SnapshotApiResponse } from "@/api/generated/model";

// Snapshot ids are decimal strings (Ruling R9), so they are compared as text, never as numbers.
export function currentSnapshot(table: CatalogTableApiResponse): SnapshotApiResponse | undefined {
  if (table.current_snapshot_id === null) return undefined;
  return table.snapshots.find((snapshot) => snapshot.id === table.current_snapshot_id);
}
