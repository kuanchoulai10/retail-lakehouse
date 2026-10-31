// Mirrors of the table-maintenance API response DTOs (snake_case kept).
// Datetimes arrive as ISO-8601 strings.

export type JsonObject = Record<string, unknown>;

export interface TableApiResponse {
  uuid: string;
  catalog: string;
  namespace: string;
  table: string;
  status: string;
  selection: string;
  settings: JsonObject | null;
  matched_rule_id: string | null;
  source_preset_id: string | null;
  operation_states: Record<string, JsonObject>;
  registered_at: string;
  updated_at: string;
}

export interface TableMetadataApiResponse {
  uuid: string;
  format_version: number;
  location: string;
  properties: Record<string, string>;
  schema_fields: JsonObject[];
  specs: JsonObject[];
  current_snapshot_id: string | null;
  snapshot_count: number;
  last_committed_at: string | null;
  total_records: number | null;
  total_data_files: number | null;
  total_delete_files: number | null;
  total_files_size_bytes: number | null;
}

export interface TableHealthOperationApiResponse {
  operation: string;
  verdict: string;
  measured: number | null;
  threshold: number | null;
  next_eligible_at: string | null;
  qualifying_partitions: number | null;
  size_bytes: number | null;
  size_source: string | null;
}

export interface TableHealthApiResponse {
  scheduled: boolean;
  not_scheduled_reason: string | null;
  operations: TableHealthOperationApiResponse[];
  position_delete_files: number;
  equality_delete_files: number;
}

export interface TableStorageReclaimedApiResponse {
  rewritten_data_files: number;
  added_data_files: number;
  rewritten_bytes: number;
  rewritten_manifests: number;
  added_manifests: number;
  expired_snapshots: number;
  deleted_data_files: number;
  deleted_manifest_files: number;
  deleted_position_delete_files: number;
  deleted_equality_delete_files: number;
}

export interface TableStorageApiResponse {
  current_bytes: number;
  current_files: number;
  old_snapshot_bytes: number;
  old_snapshot_files: number;
  window_days: number;
  reclaimed: TableStorageReclaimedApiResponse;
  attempts_without_metrics: number;
}

export interface TableCommitApiResponse {
  snapshot_id: string;
  parent_id: string | null;
  committed_at: string;
  operation: string | null;
  writer: string;
  added_records: number | null;
  deleted_records: number | null;
  added_data_files: number | null;
  deleted_data_files: number | null;
  added_delete_files: number | null;
  removed_delete_files: number | null;
  summary: Record<string, string>;
}

export interface TableCommitsApiResponse {
  items: TableCommitApiResponse[];
  truncated: boolean;
}

export interface TriggerTableMaintenanceApiResponse {
  accepted: boolean;
}

export interface TableMaintenanceRunApiResponse {
  run_id: string;
  table_uuid: string;
  execution_ref: string;
  trigger: string;
  status: string;
  operations: JsonObject[];
  created_at: string;
  finished_at: string | null;
}

export interface TableMaintenancePresetApiResponse {
  id: string;
  name: string;
  settings: JsonObject;
  created_at: string;
  updated_at: string;
}
