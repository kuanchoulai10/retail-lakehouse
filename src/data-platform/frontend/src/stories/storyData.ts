import type {
  CatalogApiResponse,
  CatalogTableApiResponse,
  NamespaceApiResponse,
  NamespaceSummaryApiResponse,
  TableApiResponse,
  TableCommitsApiResponse,
  TableDiscoveryRuleApiResponse,
  TableHealthApiResponse,
  TableIdentifierApiResponse,
  TableMaintenancePresetApiResponse,
  TableMaintenanceRunApiResponse,
  TableStorageApiResponse,
} from "@/api/generated/model";

// One small lakehouse for the page stories: catalog iceberg, namespace retail, table orders.

const STORAGE_CONFIG: CatalogApiResponse["storage_config"] = {
  storage_type: "S3",
  allowed_locations: ["s3://warehouse/iceberg"],
  endpoint: "http://rustfs.rustfs.svc.cluster.local:9000",
  endpoint_internal: null,
  path_style_access: true,
  region: "us-east-1",
  role_arn: null,
  external_id: null,
  user_arn: null,
  sts_endpoint: null,
  sts_unavailable: true,
  tenant_id: null,
  multi_tenant_app_name: null,
  consent_url: null,
  gcs_service_account: null,
};

function catalog(name: string, location: string): CatalogApiResponse {
  return {
    name,
    type: "INTERNAL",
    default_base_location: location,
    properties: { "default-base-location": location },
    storage_config: STORAGE_CONFIG,
    connection_config: null,
    entity_version: 1,
    created_at: "2026-11-01T09:00:00Z",
    updated_at: "2026-11-01T09:00:00Z",
  };
}

export const CATALOGS: CatalogApiResponse[] = [
  catalog("iceberg", "s3://warehouse/iceberg"),
  catalog("analytics", "s3://warehouse/analytics"),
];

export const NAMESPACES: NamespaceSummaryApiResponse[] = [
  { catalog: "iceberg", namespace: ["inventory"] },
  { catalog: "iceberg", namespace: ["retail"] },
];

export const RETAIL: NamespaceApiResponse = {
  catalog: "iceberg",
  namespace: ["retail"],
  properties: { location: "s3://warehouse/iceberg/retail", owner: "data-platform" },
};

export const RETAIL_TABLES: TableIdentifierApiResponse[] = [
  { catalog: "iceberg", namespace: ["retail"], name: "orders" },
  { catalog: "iceberg", namespace: ["retail"], name: "customers" },
];

export const ORDERS_UUID = "5f2b8c1e-0d4a-4c8e-9a51-7c3f0b6d2e91";

export const ORDERS: CatalogTableApiResponse = {
  catalog: "iceberg",
  namespace: ["retail"],
  name: "orders",
  uuid: ORDERS_UUID,
  format_version: 2,
  location: "s3://warehouse/iceberg/retail/orders",
  last_updated_ms: Date.parse("2026-11-09T08:30:00Z"),
  current_snapshot_id: "4812093741203984123",
  schema: {
    schema_id: 0,
    fields: [
      { id: 1, name: "order_id", type: "long", required: true, doc: "Order key from MySQL" },
      { id: 2, name: "customer_id", type: "long", required: true, doc: null },
      { id: 3, name: "amount", type: "decimal(10, 2)", required: false, doc: null },
      { id: 4, name: "ordered_at", type: "timestamptz", required: true, doc: null },
    ],
  },
  partition_spec: {
    spec_id: 0,
    fields: [{ field_id: 1000, source_id: 4, name: "ordered_at_day", transform: "day" }],
  },
  sort_order: { order_id: 0, fields: [] },
  snapshots: [
    {
      id: "4812093741203984123",
      parent_id: "3011920384710293847",
      operation: "append",
      timestamp_ms: Date.parse("2026-11-09T08:30:00Z"),
      summary: { "added-records": "1200", "added-data-files": "4" },
    },
    {
      id: "3011920384710293847",
      parent_id: null,
      operation: "append",
      timestamp_ms: Date.parse("2026-11-09T07:30:00Z"),
      summary: { "added-records": "980", "added-data-files": "3" },
    },
  ],
  properties: { "write.format.default": "parquet", "commit.retry.num-retries": "4" },
  summary: { total_records: 2180, total_data_files: 7, total_files_size: 1_824_310 },
};

export const MAINTAINED_ORDERS: TableApiResponse = {
  uuid: ORDERS_UUID,
  catalog: "iceberg",
  namespace: "retail",
  table: "orders",
  status: "active",
  selection: "auto",
  settings: {},
  matched_rule_id: "rule-retail",
  source_preset_id: "preset-default",
  operation_states: {},
  registered_at: "2026-11-02T10:00:00Z",
  updated_at: "2026-11-09T08:00:00Z",
};

export const MAINTAINED_TABLES: TableApiResponse[] = [
  MAINTAINED_ORDERS,
  {
    ...MAINTAINED_ORDERS,
    uuid: "9c0e7a44-6b1f-4f0a-8d2e-1a5b3c7d9e02",
    table: "customers",
    status: "paused",
    selection: "manual",
  },
  {
    ...MAINTAINED_ORDERS,
    uuid: "1d3f5b7a-2c4e-4a6b-8c0d-e2f4a6b8c0d1",
    namespace: "inventory",
    table: "stock_levels",
  },
];

export const HEALTH: TableHealthApiResponse = {
  scheduled: true,
  not_scheduled_reason: null,
  operations: [
    {
      operation: "rewrite_data_files",
      verdict: "due",
      measured: 12,
      threshold: 5,
      next_eligible_at: null,
      qualifying_partitions: 3,
      size_bytes: null,
      size_source: null,
    },
    {
      operation: "expire_snapshots",
      verdict: "not_due",
      measured: 2,
      threshold: 20,
      next_eligible_at: null,
      qualifying_partitions: null,
      size_bytes: null,
      size_source: null,
    },
  ],
  position_delete_files: 0,
  equality_delete_files: 0,
};

export const STORAGE: TableStorageApiResponse = {
  current_bytes: 1_824_310,
  current_files: 7,
  old_snapshot_bytes: 512_000,
  old_snapshot_files: 2,
  window_days: 30,
  attempts_without_metrics: 0,
  reclaimed: {
    rewritten_data_files: 14,
    added_data_files: 2,
    rewritten_bytes: 3_400_000,
    rewritten_manifests: 0,
    added_manifests: 0,
    expired_snapshots: 6,
    deleted_data_files: 9,
    deleted_manifest_files: 3,
  },
};

export const COMMITS: TableCommitsApiResponse = {
  truncated: false,
  items: [
    {
      snapshot_id: "4812093741203984123",
      parent_id: "4718203948123094812",
      committed_at: "2026-11-09T08:30:00Z",
      operation: "append",
      writer: "kafka_connect",
      added_data_files: 4,
      deleted_data_files: 0,
      added_delete_files: 0,
      removed_delete_files: 0,
      added_records: 1200,
      deleted_records: 0,
      summary: {},
    },
    {
      snapshot_id: "4718203948123094812",
      parent_id: "4610293847561029384",
      committed_at: "2026-11-09T02:15:00Z",
      operation: "append",
      writer: "kafka_connect",
      added_data_files: 3,
      deleted_data_files: 0,
      added_delete_files: 0,
      removed_delete_files: 0,
      added_records: 860,
      deleted_records: 0,
      summary: {},
    },
    {
      snapshot_id: "4610293847561029384",
      parent_id: "4502938475610293847",
      committed_at: "2026-11-08T02:03:00Z",
      operation: "replace",
      writer: "spark",
      added_data_files: 2,
      deleted_data_files: 18,
      added_delete_files: 0,
      removed_delete_files: 0,
      added_records: null,
      deleted_records: null,
      summary: { "spark.app.id": "spark-application-1762567380" },
    },
    {
      snapshot_id: "4502938475610293847",
      parent_id: "4401928374650192837",
      committed_at: "2026-11-07T16:40:00Z",
      operation: "delete",
      writer: "spark",
      added_data_files: 0,
      deleted_data_files: 0,
      added_delete_files: 0,
      removed_delete_files: 0,
      added_records: 0,
      deleted_records: 42,
      summary: {},
    },
    {
      snapshot_id: "4401928374650192837",
      parent_id: "3011920384710293847",
      committed_at: "2026-11-07T09:05:00Z",
      operation: "append",
      writer: "kafka_connect",
      added_data_files: 5,
      deleted_data_files: 0,
      added_delete_files: 0,
      removed_delete_files: 0,
      added_records: 2310,
      deleted_records: 0,
      summary: {},
    },
  ],
};

export const RUNS: TableMaintenanceRunApiResponse[] = [
  {
    run_id: "run-1",
    table_uuid: ORDERS_UUID,
    execution_ref: `table-maintenance:table=${ORDERS_UUID}:run=run-1`,
    trigger: "scheduled",
    status: "succeeded",
    created_at: "2026-11-08T02:00:00Z",
    finished_at: "2026-11-08T02:03:10Z",
    operations: [
      {
        operation: "rewrite_data_files",
        status: "succeeded",
        attempts: 1,
        started_at: "2026-11-08T02:00:00Z",
        finished_at: "2026-11-08T02:03:10Z",
        job_name: "tm-orders-rewrite",
        metrics: { rewritten_data_files_count: 14 },
        error: null,
        expected_files: null,
      },
    ],
  },
];

export const PRESETS: TableMaintenancePresetApiResponse[] = [
  {
    id: "preset-default",
    name: "default",
    settings: {
      reconcile_interval_seconds: 3600,
      rewrite_data_files: { enabled: true, min_interval_seconds: 3600, target_file_size_bytes: null },
      expire_snapshots: { enabled: true, older_than_seconds: 604800, retain_last: 5 },
      remove_orphan_files: { enabled: false, older_than_seconds: 259200 },
    },
    created_at: "2026-11-01T09:00:00Z",
    updated_at: "2026-11-01T09:00:00Z",
  },
];

export const RULES: TableDiscoveryRuleApiResponse[] = [
  {
    id: "rule-retail",
    priority: 10,
    effect: "include",
    catalog_pattern: "iceberg",
    namespace_pattern: "retail",
    table_pattern: "*",
    preset_id: "preset-default",
    enabled: true,
    created_at: "2026-11-01T09:00:00Z",
    updated_at: "2026-11-01T09:00:00Z",
  },
  {
    id: "rule-tmp",
    priority: 50,
    effect: "exclude",
    catalog_pattern: "*",
    namespace_pattern: "*",
    table_pattern: "tmp_*",
    preset_id: null,
    enabled: false,
    created_at: "2026-11-01T09:00:00Z",
    updated_at: "2026-11-01T09:00:00Z",
  },
];
