import type { TableApiResponse, TableMetadataApiResponse } from "../api/types";

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function tableFixture(overrides: Partial<TableApiResponse> = {}): TableApiResponse {
  return {
    uuid: "uuid-orders",
    catalog: "iceberg",
    namespace: "inventory",
    table: "orders",
    status: "active",
    selection: "auto",
    settings: null,
    matched_rule_id: "rule-1",
    source_preset_id: "default",
    operation_states: {},
    registered_at: "2026-10-30T10:00:00Z",
    updated_at: "2026-10-31T08:00:00Z",
    ...overrides,
  };
}

export function metadataFixture(
  overrides: Partial<TableMetadataApiResponse> = {},
): TableMetadataApiResponse {
  return {
    uuid: "uuid-orders",
    format_version: 2,
    location: "s3://warehouse/inventory/orders",
    properties: { "write.format.default": "parquet", "commit.retry.num-retries": "4" },
    schema_fields: [],
    specs: [],
    current_snapshot_id: 42,
    snapshot_count: 17,
    last_committed_at: new Date(Date.now() - 3 * 3600_000).toISOString(),
    total_records: 1204331,
    total_data_files: 100,
    total_delete_files: 0,
    total_files_size_bytes: 335544320,
    ...overrides,
  };
}
