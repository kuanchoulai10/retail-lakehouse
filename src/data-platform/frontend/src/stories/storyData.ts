import type {
  CatalogApiResponse,
  CatalogTableApiResponse,
  CatalogTablePartitionSpecComparisonApiResponse,
  CatalogTablePartitionSpecVersionsApiResponse,
  CatalogTablePropertiesApiResponse,
  CatalogTableSchemaComparisonApiResponse,
  CatalogTableSchemaVersionsApiResponse,
  DiscoveryEffectivePolicyApiResponse,
  EffectivePoliciesApiResponse,
  ListedTableDiscoveryPolicyApiResponse,
  ListedTableDiscoveryPolicyAttachmentApiResponse,
  ListedTableMaintenancePolicyApiResponse,
  ListedTableMaintenancePolicyMappingApiResponse,
  MaintenanceEffectivePolicyApiResponse,
  NamespaceApiResponse,
  PolicyTargetApiResponse,
  NamespaceSummaryApiResponse,
  PartitionFieldComparisonApiResponse,
  PlatformSettingApiResponse,
  PlatformSettingsApiResponse,
  PlatformSettingsGroupApiResponse,
  ReconciliationOperationApiResponse,
  ScannedCatalogsApiResponse,
  SchemaFieldComparisonApiResponse,
  TableApiResponse,
  TableCommitsApiResponse,
  TableCurrentMetricsApiResponse,
  TableDiscoveryPolicyVersionApiResponse,
  TableIdentifierApiResponse,
  TableMaintenanceRunApiResponse,
  TableMaintenanceRunAttemptApiResponse,
  TableMetricTrendsApiResponse,
  TableMetricValuesApiResponse,
  TableReconciliationApiResponse,
} from "@/api/generated/model";
import type { PolicyContent } from "@/lib/policyDraft";

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

// The discovery policy and rules that decided the maintained tables (CORE_TABLES below).
export const CORE_TABLES_POLICY_ID = "dp-01m7s6c3tqee0rhg00xry2zqqn";
const CORE_ORDERS_RULE_ID = "dr-01m7s6c3tqee0rhg00xry2zqqp";
const CORE_STOCK_RULE_ID = "dr-01m7s6c3tqee0rhg00xry2zqqq";

export const DEFAULT_POLICY_ID = "mp-00000000000000000000000000";
export const RETAIL_NIGHTLY_POLICY_ID = "mp-01m7sd16b1ef2vww335cwcg9k7";
const SCRATCH_POLICY_ID = "mp-01m7sd16b1ef2vww335jk8dm9t";

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
    schema_id: 1,
    fields: [
      { id: 1, name: "order_id", type: "long", required: true, doc: "Order key from MySQL" },
      { id: 2, name: "customer_id", type: "long", required: true, doc: null },
      { id: 3, name: "amount", type: "decimal(10, 2)", required: false, doc: null },
      { id: 4, name: "ordered_at", type: "timestamptz", required: true, doc: null },
      { id: 5, name: "coupon_code", type: "string", required: false, doc: null },
      { id: 6, name: "shipping", type: "struct<city: string, zip: string>", required: false, doc: null },
      { id: 9, name: "channel", type: "string", required: false, doc: null },
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
      schema_id: 1,
      summary: { "added-records": "1200", "added-data-files": "4" },
    },
    {
      id: "3011920384710293847",
      parent_id: null,
      operation: "append",
      timestamp_ms: Date.parse("2026-11-09T07:30:00Z"),
      schema_id: 0,
      summary: { "added-records": "980", "added-data-files": "3" },
    },
  ],
  properties: {
    "write.format.default": "parquet",
    "commit.retry.num-retries": "4",
    "write.target-file-size-bytes": "134217728",
    "gc.enabled": "false",
    "created-at": "2026-11-09T07:00:00Z",
    owner: "data-eng",
  },
  summary: { total_records: 2180, total_data_files: 7, total_files_size: 1_824_310 },
};

// The Properties tab of orders: every known property next to its default. The table sets two at their
// default, one away from it, a custom owner, and the catalog forces gc off. Polaris wrote created-at.
export const ORDERS_PROPERTIES: CatalogTablePropertiesApiResponse = {
  uuid: ORDERS_UUID,
  iceberg_version: "1.10.1",
  properties: [
    {
      key: "commit.retry.num-retries",
      current_value: "4",
      default_value: "4",
      default_source: "iceberg",
      modified: false,
      custom: false,
      resettable: true,
      description: "How many times a failed commit is retried.",
    },
    {
      key: "created-at",
      current_value: "2026-11-09T07:00:00Z",
      default_value: null,
      default_source: null,
      modified: false,
      custom: false,
      resettable: false,
      description: "When Polaris created the table; written by Polaris.",
    },
    {
      key: "format-version",
      current_value: "2",
      default_value: "2",
      default_source: "iceberg",
      modified: false,
      custom: false,
      resettable: false,
      description: "Table format version; fixed at create and only ever upgraded, never removed.",
    },
    {
      key: "gc.enabled",
      current_value: "false",
      default_value: "false",
      default_source: "catalog_override",
      modified: false,
      custom: false,
      resettable: false,
      description:
        "Allow snapshot expiry and orphan file removal to delete files; not reset by Reset to default, edit it deliberately.",
    },
    {
      key: "history.expire.max-snapshot-age-ms",
      current_value: null,
      default_value: "432000000",
      default_source: "iceberg",
      modified: false,
      custom: false,
      resettable: true,
      description: "Age in milliseconds after which expiry removes a snapshot (5 days).",
    },
    {
      key: "owner",
      current_value: "data-eng",
      default_value: null,
      default_source: null,
      modified: true,
      custom: true,
      resettable: true,
      description: null,
    },
    {
      key: "write.format.default",
      current_value: "parquet",
      default_value: "parquet",
      default_source: "iceberg",
      modified: false,
      custom: false,
      resettable: true,
      description: "File format of new data files.",
    },
    {
      key: "write.target-file-size-bytes",
      current_value: "134217728",
      default_value: "536870912",
      default_source: "iceberg",
      modified: true,
      custom: false,
      resettable: true,
      description: "Target size of a data file in bytes (512 MiB); compaction aims for it too.",
    },
  ],
};

export const MAINTAINED_ORDERS: TableApiResponse = {
  uuid: ORDERS_UUID,
  catalog: "iceberg",
  namespace: "retail",
  table: "orders",
  status: "managed",
  priority: "P3",
  matched_rule_id: CORE_ORDERS_RULE_ID,
  matched_policy_id: CORE_TABLES_POLICY_ID,
  matched_policy_version: 1,
  operation_states: {},
  registered_at: "2026-11-02T10:00:00Z",
  updated_at: "2026-11-09T08:00:00Z",
  last_committed_at: "2026-11-09T07:30:00Z",
  last_discovered_at: "2026-11-09T08:10:00Z",
};

export const MAINTAINED_TABLES: TableApiResponse[] = [
  MAINTAINED_ORDERS,
  {
    ...MAINTAINED_ORDERS,
    uuid: "9c0e7a44-6b1f-4f0a-8d2e-1a5b3c7d9e02",
    table: "customers",
    status: "unmanaged",
    matched_rule_id: null,
    last_committed_at: null,
  },
  {
    ...MAINTAINED_ORDERS,
    uuid: "1d3f5b7a-2c4e-4a6b-8c0d-e2f4a6b8c0d1",
    namespace: "inventory",
    table: "stock_levels",
    matched_rule_id: CORE_STOCK_RULE_ID,
  },
  {
    ...MAINTAINED_ORDERS,
    uuid: "5e7a9c1b-3d5f-4b7c-9e1a-b3d5f7a9c1e3",
    table: "legacy_orders",
    status: "dropped",
    matched_rule_id: null,
    last_committed_at: "2026-11-05T16:20:00Z",
    last_discovered_at: "2026-11-06T09:00:00Z",
  },
];

function schemaRow(
  id: number,
  path: string[],
  type: string,
  required: boolean,
  overrides: Partial<SchemaFieldComparisonApiResponse> = {},
): SchemaFieldComparisonApiResponse {
  return {
    field_id: id,
    depth: path.length - 1,
    path,
    previous_path: path,
    type,
    previous_type: type,
    required,
    previous_required: required,
    doc: null,
    previous_doc: null,
    changes: [],
    ...overrides,
  };
}

function addedRow(id: number, path: string[], type: string): SchemaFieldComparisonApiResponse {
  return schemaRow(id, path, type, false, {
    previous_path: null,
    previous_type: null,
    previous_required: null,
    changes: ["added"],
  });
}

function removedRow(id: number, path: string[], type: string): SchemaFieldComparisonApiResponse {
  return schemaRow(id, path, type, false, {
    path: null,
    type: null,
    required: null,
    previous_path: path,
    previous_type: type,
    previous_required: false,
    changes: ["removed"],
  });
}

const orderIdDocChanged = (doc: string | null, previousDoc: string | null) =>
  schemaRow(1, ["order_id"], "long", true, { doc, previous_doc: previousDoc, changes: ["doc_changed"] });

const ORDERS_V0_ROWS = [
  schemaRow(2, ["customer_id"], "long", true),
  schemaRow(3, ["amount"], "decimal(10, 2)", false),
  schemaRow(4, ["ordered_at"], "timestamptz", true),
];

// orders has two schema versions: v0 has the four columns the table was created with; v1 added five
// fields (coupon_code, the shipping struct with its two children, channel) and documented order_id.
export const ORDERS_SCHEMA_VERSIONS: CatalogTableSchemaVersionsApiResponse = {
  current_schema_id: 1,
  versions: [
    {
      schema_id: 1,
      previous_schema_id: 0,
      current: true,
      column_count: 9,
      changes: { added: 5, removed: 0, renamed: 0, type_changed: 0, nullability_changed: 0, doc_changed: 1 },
    },
    { schema_id: 0, previous_schema_id: null, current: false, column_count: 4, changes: null },
  ],
};

// The comparison the page asks for: `base` is null when the url names none (the previous version).
export function ordersSchemaComparison(schemaId: number, base: number | null): CatalogTableSchemaComparisonApiResponse {
  if (schemaId === 1 && (base === null || base === 0)) {
    return {
      schema_id: 1,
      base_schema_id: 0,
      fields: [
        orderIdDocChanged("Order key from MySQL", null),
        ...ORDERS_V0_ROWS,
        addedRow(5, ["coupon_code"], "string"),
        addedRow(6, ["shipping"], "struct"),
        { ...addedRow(7, ["shipping", "city"], "string"), depth: 1 },
        { ...addedRow(8, ["shipping", "zip"], "string"), depth: 1 },
        addedRow(9, ["channel"], "string"),
      ],
    };
  }
  if (schemaId === 0 && base === null) {
    return {
      schema_id: 0,
      base_schema_id: null,
      fields: [schemaRow(1, ["order_id"], "long", true), ...ORDERS_V0_ROWS],
    };
  }
  if (schemaId === 0 && base === 1) {
    return {
      schema_id: 0,
      base_schema_id: 1,
      fields: [
        orderIdDocChanged(null, "Order key from MySQL"),
        ...ORDERS_V0_ROWS,
        removedRow(5, ["coupon_code"], "string"),
        removedRow(6, ["shipping"], "struct"),
        { ...removedRow(7, ["shipping", "city"], "string"), depth: 1 },
        { ...removedRow(8, ["shipping", "zip"], "string"), depth: 1 },
        removedRow(9, ["channel"], "string"),
      ],
    };
  }
  throw new Error(`no story comparison of schema ${schemaId} with ${base ?? "the previous version"}`);
}

// A long history: ids 0..count-1 (newest first), each adding one column, the newest current.
export function ordersManySchemaVersions(count: number): CatalogTableSchemaVersionsApiResponse {
  return {
    current_schema_id: count - 1,
    versions: Array.from({ length: count }, (_, index) => {
      const id = count - 1 - index;
      return {
        schema_id: id,
        previous_schema_id: id === 0 ? null : id - 1,
        current: id === count - 1,
        column_count: 4 + id,
        changes:
          id === 0 ? null : { added: 1, removed: 0, renamed: 0, type_changed: 0, nullability_changed: 0, doc_changed: 0 },
      };
    }),
  };
}

function partitionRow(overrides: Partial<PartitionFieldComparisonApiResponse>): PartitionFieldComparisonApiResponse {
  return {
    field_id: 1000,
    previous_field_id: 1000,
    name: "ordered_at_day",
    previous_name: "ordered_at_day",
    transform: "day",
    previous_transform: "day",
    expression: "day(ordered_at)",
    previous_expression: "day(ordered_at)",
    source_path: ["ordered_at"],
    previous_source_path: ["ordered_at"],
    changes: [],
    ...overrides,
  };
}

// orders has one partition spec: day(ordered_at).
export const ORDERS_SPEC_VERSIONS: CatalogTablePartitionSpecVersionsApiResponse = {
  default_spec_id: 0,
  versions: [{ spec_id: 0, previous_spec_id: null, default: true, field_count: 1, changes: null }],
};

export function ordersSpecComparison(specId: number): CatalogTablePartitionSpecComparisonApiResponse {
  return { spec_id: specId, base_spec_id: null, fields: [partitionRow({})] };
}

// The same table once its partitioning went from day to hour: v1 is the default.
export const ORDERS_HOURLY_SPEC_VERSIONS: CatalogTablePartitionSpecVersionsApiResponse = {
  default_spec_id: 1,
  versions: [
    {
      spec_id: 1,
      previous_spec_id: 0,
      default: true,
      field_count: 1,
      changes: { added: 0, removed: 0, renamed: 0, transform_changed: 1 },
    },
    ORDERS_SPEC_VERSIONS.versions[0]!,
  ],
};

export const ORDERS_HOURLY_SPEC_COMPARISON: CatalogTablePartitionSpecComparisonApiResponse = {
  spec_id: 1,
  base_spec_id: 0,
  fields: [
    partitionRow({
      field_id: 1001,
      name: "ordered_at_hour",
      transform: "hour",
      expression: "hour(ordered_at)",
      changes: ["transform_changed"],
    }),
  ],
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
      schema_id: 1,
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
      schema_id: 1,
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
      schema_id: 0,
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
      schema_id: 0,
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
      schema_id: 0,
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

export const SCHEDULED_RUN_ID = "mr-01m6we4j80f049yj9fq93t3z57";
export const SCHEDULED_MANIFESTS_RUN_ID = "mr-01m6we4j80f049yj9fq93t3z58";
export const SCHEDULED_EXPIRE_RUN_ID = "mr-01m6we4j80f049yj9fq93t3z59";
export const SCHEDULED_ORPHANS_RUN_ID = "mr-01m6we4j80f049yj9fq93t3z5a";
export const ESCALATED_RUN_ID = "mr-01m6z0h980ebq90tzxr5xezxae";
// A run older than the latest 50 the list returns: only the read by id answers it.
export const OLDER_RUN_ID = "mr-01m3p7k2c0d9e8f6g5h4j3k2m1";

type Attempt = TableMaintenanceRunAttemptApiResponse;

// An attempt that ran at S and succeeded, as most attempts do.
function succeededAttempt(jobName: string, startedAt: string, finishedAt: string): Attempt {
  return {
    attempt: 1,
    size: "S",
    status: "succeeded",
    started_at: startedAt,
    started_running_at: startedAt,
    finished_at: finishedAt,
    failure_class: null,
    error: null,
    event_log_finished: true,
    next_step: "done",
    next_size: null,
    job_name: jobName,
  };
}

// One run of one operation that ended: every field a run has, the attempts its timeline.
function endedRun(
  runId: string,
  operation: string,
  attempts: Attempt[],
  overrides: Partial<TableMaintenanceRunApiResponse> = {},
): TableMaintenanceRunApiResponse {
  return {
    run_id: runId,
    table_uuid: ORDERS_UUID,
    execution_ref: `table-maintenance:table-uuid=${ORDERS_UUID}`,
    trigger: "scheduled",
    operation,
    priority: "P3",
    status: "succeeded",
    created_at: "2026-11-08T02:00:00Z",
    started_at: attempts[0]?.started_at ?? null,
    finished_at: attempts.at(-1)?.finished_at ?? null,
    filters: [],
    procedure_args: {},
    metrics: {},
    error: null,
    skip_reason: null,
    attempts,
    ...overrides,
  };
}

// The scheduled plan's compaction, its first run.
const SCHEDULED_COMPACTION_RUN: TableMaintenanceRunApiResponse = endedRun(
  SCHEDULED_RUN_ID,
  "rewrite_data_files",
  [succeededAttempt("tm-orders-rewrite", "2026-11-08T02:00:00Z", "2026-11-08T02:03:10Z")],
  {
    filters: [{ spec_id: 0, where: "(`region` = 'eu')" }],
    procedure_args: { options: { "target-file-size-bytes": 134217728 } },
    metrics: { rewritten_data_files_count: 14 },
  },
);

// The four runs of one scheduled plan, created together and run one at a time in the plan's order,
// listed as the API lists them: newest first, the plan's last operation first.
export const RUNS: TableMaintenanceRunApiResponse[] = [
  endedRun(
    SCHEDULED_ORPHANS_RUN_ID,
    "remove_orphan_files",
    [succeededAttempt("tm-orders-orphans", "2026-11-08T02:04:50Z", "2026-11-08T02:05:30Z")],
    { procedure_args: { older_than: "2026-11-05T02:00:00+00:00" }, metrics: { orphan_file_location_count: 3 } },
  ),
  endedRun(
    SCHEDULED_EXPIRE_RUN_ID,
    "expire_snapshots",
    [succeededAttempt("tm-orders-expire", "2026-11-08T02:04:10Z", "2026-11-08T02:04:40Z")],
    {
      procedure_args: { older_than: "2026-11-03T02:00:00+00:00", retain_last: 5 },
      metrics: { deleted_data_files_count: 42, deleted_manifest_files_count: 6 },
    },
  ),
  endedRun(
    SCHEDULED_MANIFESTS_RUN_ID,
    "rewrite_manifests",
    [succeededAttempt("tm-orders-manifests", "2026-11-08T02:03:20Z", "2026-11-08T02:04:00Z")],
    { metrics: { rewritten_manifests_count: 18, added_manifests_count: 2 } },
  ),
  SCHEDULED_COMPACTION_RUN,
];

// A compaction that ran out of memory at S and succeeded at M.
export const ESCALATED_RUN: TableMaintenanceRunApiResponse = endedRun(
  ESCALATED_RUN_ID,
  "rewrite_data_files",
  [
    {
      attempt: 1,
      size: "S",
      status: "failed",
      started_at: "2026-11-09T02:00:00Z",
      started_running_at: "2026-11-09T02:00:00Z",
      finished_at: "2026-11-09T02:02:10Z",
      failure_class: "oom",
      error: "Py4JJavaError: An error occurred while calling o61.sql. java.lang.OutOfMemoryError: Java heap space",
      event_log_finished: false,
      next_step: "retry_larger",
      next_size: "M",
      job_name: "tm-orders-rewrite-2-a1",
    },
    {
      attempt: 2,
      size: "M",
      status: "succeeded",
      started_at: "2026-11-09T02:03:20Z",
      started_running_at: "2026-11-09T02:03:20Z",
      finished_at: "2026-11-09T02:09:40Z",
      failure_class: null,
      error: null,
      event_log_finished: true,
      next_step: "done",
      next_size: null,
      job_name: "tm-orders-rewrite-2-a2",
    },
  ],
  {
    trigger: "manual",
    created_at: "2026-11-09T02:00:00Z",
    procedure_args: { options: { "target-file-size-bytes": 134217728 } },
    metrics: { rewritten_data_files_count: 24, peak_driver_heap_bytes: 612368384, peak_executor_heap_bytes: 1140850688 },
  },
);

export const PARTITION_SCOPE_RUN_ID = "mr-01m8c2v7e0k3b9x4d5n6q1w2yb";

const TEN_PARTITIONS_WHERE = Array.from(
  { length: 10 },
  (_, day) => `(\`region\` = 'eu' AND \`order_day\` = DATE '2026-11-${String(day + 10).padStart(2, "0")}')`,
).join(" OR ");

// A scheduled compaction of the partitions over the target: one where clause per partition spec, the first of them long.
export const PARTITION_SCOPE_RUN: TableMaintenanceRunApiResponse = {
  ...SCHEDULED_COMPACTION_RUN,
  run_id: PARTITION_SCOPE_RUN_ID,
  filters: [
    { spec_id: 0, where: TEN_PARTITIONS_WHERE },
    { spec_id: 1, where: "(`order_hour` = TIMESTAMP '2026-11-19 03:00:00')" },
  ],
};

// An expiry from October, older than the latest 50 runs the list returns.
export const OLDER_RUN: TableMaintenanceRunApiResponse = endedRun(
  OLDER_RUN_ID,
  "expire_snapshots",
  [succeededAttempt("tm-orders-expire-old", "2026-10-01T02:00:00Z", "2026-10-01T02:00:40Z")],
  {
    created_at: "2026-10-01T02:00:00Z",
    procedure_args: { older_than: "2026-09-26T02:00:00+00:00", retain_last: 5 },
    metrics: { deleted_data_files_count: 7 },
  },
);

export const IN_FLIGHT_RUN_ID = "mr-01m7bk4q80f3dt6ywe2m5c1h9a";
export const PENDING_RUN_ID = "mr-01m7bk4q80f3dt6ywe2m5c1h9b";
export const QUEUE_TIMEOUT_RUN_ID = "mr-01m7bk9d30ff8e5hn7a2xk4b6c";
const MINUTE_MS = 60_000;

// A manual compaction made of these attempts, created when its first attempt was submitted.
function runOfAttempts(
  runId: string,
  status: string,
  attempts: Attempt[],
  finishedAt: string | null,
): TableMaintenanceRunApiResponse {
  return endedRun(runId, "rewrite_data_files", attempts, {
    trigger: "manual",
    priority: "P1",
    status,
    created_at: attempts[0]!.started_at,
    finished_at: finishedAt,
    procedure_args: { options: { "target-file-size-bytes": 134217728 } },
  });
}

// The first attempt of a run in flight ran out of memory at S. A story builds the run when it starts, so its
// queued and running times count from the moment the story opens and no assertion depends on the date.
function outOfMemoryAtS(minutesAgo: (minutes: number) => string): Attempt {
  return {
    attempt: 1,
    size: "S",
    status: "failed",
    started_at: minutesAgo(40),
    started_running_at: minutesAgo(38),
    finished_at: minutesAgo(33),
    failure_class: "oom",
    error: null,
    event_log_finished: false,
    next_step: "retry_larger",
    next_size: "M",
    job_name: "tm-orders-rewrite-live-a1",
  };
}

function attemptAtM(overrides: Partial<Attempt>): Attempt {
  return {
    attempt: 2,
    size: "M",
    status: "running",
    started_at: "",
    started_running_at: null,
    finished_at: null,
    failure_class: null,
    error: null,
    event_log_finished: null,
    next_step: null,
    next_size: null,
    job_name: "tm-orders-rewrite-live-a2",
    ...overrides,
  };
}

function agoFrom(now: Date): (minutes: number) => string {
  return (minutes) => new Date(now.getTime() - minutes * MINUTE_MS).toISOString();
}

// A run in flight: the larger attempt waited 7 minutes in the queue and has been running for 18.
export function inFlightRun(now: Date = new Date()): TableMaintenanceRunApiResponse {
  const minutesAgo = agoFrom(now);
  return runOfAttempts(
    IN_FLIGHT_RUN_ID,
    "running",
    [outOfMemoryAtS(minutesAgo), attemptAtM({ started_at: minutesAgo(25), started_running_at: minutesAgo(18) })],
    null,
  );
}

// The next run of inFlightRun's plan, created with it: it waits, with no attempt, until the
// compaction ends. It lists above the compaction, as the plan's later operation.
export function pendingRun(now: Date = new Date()): TableMaintenanceRunApiResponse {
  return endedRun(PENDING_RUN_ID, "expire_snapshots", [], {
    trigger: "manual",
    priority: "P1",
    status: "pending",
    created_at: agoFrom(now)(40),
    procedure_args: { older_than: agoFrom(now)(40 + 5 * 24 * 60), retain_last: 5 },
  });
}

// The same run (same id) earlier in its life: the larger attempt still waits in its Volcano queue.
export function queuedRun(now: Date = new Date()): TableMaintenanceRunApiResponse {
  const minutesAgo = agoFrom(now);
  return runOfAttempts(
    IN_FLIGHT_RUN_ID,
    "running",
    [outOfMemoryAtS(minutesAgo), attemptAtM({ status: "queued", started_at: minutesAgo(4) })],
    null,
  );
}

// An attempt that waited the whole queue limit and never ran; every time is fixed, as it has ended.
export const QUEUE_TIMEOUT_RUN = runOfAttempts(
  QUEUE_TIMEOUT_RUN_ID,
  "failed",
  [
    attemptAtM({
      attempt: 1,
      size: "S",
      status: "failed",
      started_at: "2026-11-18T02:00:00Z",
      finished_at: "2026-11-19T02:00:00Z",
      failure_class: "queue_timeout",
      next_step: "not_retried",
      job_name: "tm-orders-rewrite-timeout-a1",
    }),
  ],
  "2026-11-19T02:00:00Z",
);

export const DEFAULT_DISCOVERY_POLICY_ID = "dp-00000000000000000000000000";
export const SALES_TABLES_POLICY_ID = "dp-01m7s6c3tqee0rhg00xry2zqqv";

// The platform default, which manages nothing.
const DEFAULT_DISCOVERY_POLICY: ListedTableDiscoveryPolicyApiResponse = {
  id: DEFAULT_DISCOVERY_POLICY_ID,
  name: "default",
  is_default: true,
  version: 1,
  description: "Manages nothing. Attach another discovery policy to a catalog, namespace or table to manage its tables.",
  no_match_outcome: "unmanage",
  rules: [],
  attachment_count: 0,
  created_at: "2026-11-01T09:00:00Z",
  updated_at: "2026-11-01T09:00:00Z",
};

// core-tables, attached to catalog iceberg: MAINTAINED_ORDERS names its v1 and rule 1, the
// inventory stock table its rule 2; every other table there is not managed.
export const CORE_TABLES: ListedTableDiscoveryPolicyApiResponse = {
  id: CORE_TABLES_POLICY_ID,
  name: "core-tables",
  is_default: false,
  version: 1,
  description: "Retail orders and inventory stock levels",
  no_match_outcome: "unmanage",
  rules: [
    {
      id: CORE_ORDERS_RULE_ID,
      outcome: "manage",
      conditions: [
        { attribute: "namespace", operator: "glob", values: ["retail"] },
        { attribute: "table_name", operator: "glob", values: ["orders"] },
      ],
    },
    {
      id: CORE_STOCK_RULE_ID,
      outcome: "manage",
      conditions: [
        { attribute: "namespace", operator: "glob", values: ["inventory"] },
        { attribute: "table_name", operator: "glob", values: ["stock_*"] },
      ],
    },
  ],
  attachment_count: 1,
  created_at: "2026-11-02T09:00:00Z",
  updated_at: "2026-11-02T09:00:00Z",
};

// sales-tables, which manages the sales namespaces except their temporary tables, attached to
// namespace iceberg.sales.
export const SALES_TABLES: ListedTableDiscoveryPolicyApiResponse = {
  id: SALES_TABLES_POLICY_ID,
  name: "sales-tables",
  is_default: false,
  version: 2,
  description: "Sales tables, without the temporary ones",
  no_match_outcome: "unmanage",
  rules: [
    {
      id: "dr-01m7s6c3tqee0rhg00xry2zqqt",
      outcome: "manage",
      conditions: [
        { attribute: "namespace", operator: "glob", values: ["sales", "sales.*"] },
        { attribute: "table_name", operator: "glob", values: ["orders*", "returns*"] },
      ],
    },
    {
      id: "dr-01m7s6c3tqee0rhg00xz1dk9cs",
      outcome: "unmanage",
      conditions: [{ attribute: "table_name", operator: "glob", values: ["tmp_*", "staging_*"] }],
    },
  ],
  attachment_count: 1,
  created_at: "2026-11-01T09:00:00Z",
  updated_at: "2026-11-05T09:00:00Z",
};

// As the API lists them: the default first, then by name.
export const DISCOVERY_POLICIES: ListedTableDiscoveryPolicyApiResponse[] = [
  DEFAULT_DISCOVERY_POLICY,
  CORE_TABLES,
  SALES_TABLES,
];

// The kept versions before each policy's current one. sales-tables v1 kept archive tables out
// where v2 keeps temporary ones out: v2 added one rule and removed one.
export const DISCOVERY_POLICY_VERSIONS: TableDiscoveryPolicyVersionApiResponse[] = [
  {
    id: SALES_TABLES_POLICY_ID,
    name: "sales-tables",
    is_default: false,
    version: 1,
    description: "Sales tables, without the temporary ones",
    no_match_outcome: "unmanage",
    rules: [
      SALES_TABLES.rules[0]!,
      {
        id: "dr-01m7s6c3tqee0rhg00xz1dk9ct",
        outcome: "unmanage",
        conditions: [{ attribute: "table_name", operator: "glob", values: ["archive_*"] }],
      },
    ],
    created_at: "2026-11-01T09:00:00Z",
  },
];

export const DISCOVERY_POLICY_ATTACHMENTS: ListedTableDiscoveryPolicyAttachmentApiResponse[] = [
  {
    id: "da-01m7s6c3tqee0rhg00xry2zqqx",
    policy_id: SALES_TABLES_POLICY_ID,
    policy_name: "sales-tables",
    target: { type: "namespace", path: ["iceberg", "sales"], table_uuid: null },
    orphaned: false,
    attached_at: "2026-11-05T09:00:00Z",
  },
  {
    id: "da-01m7s6c3tqee0rhg00xry2zqqz",
    policy_id: CORE_TABLES_POLICY_ID,
    policy_name: "core-tables",
    target: { type: "catalog", path: ["iceberg"], table_uuid: null },
    orphaned: false,
    attached_at: "2026-11-02T09:00:00Z",
  },
];

// Discovery scans iceberg, where core-tables and sales-tables are attached, and reads it.
export const SCANNED_CATALOGS: ScannedCatalogsApiResponse = {
  catalogs: [{ catalog: "iceberg", last_discovered_at: "2026-11-09T08:10:00Z", failure: null }],
};

const QUIET_OPERATIONS: ReconciliationOperationApiResponse[] = [
  {
    operation: "rewrite_data_files",
    result: "not_needed",
    measurements: [
      { key: "reducible_files", observed: 0, unit: "count", threshold: 5, comparison: ">=", met: false },
      { key: "target_file_size", observed: 134217728, unit: "bytes", threshold: null, comparison: null, met: null },
      { key: "qualifying_partitions", observed: 0, unit: "count", threshold: null, comparison: null, met: null },
    ],
    next_eligible_at: null,
    run_id: null,
  },
  {
    operation: "rewrite_manifests",
    result: "not_needed",
    measurements: [{ key: "small_manifests", observed: 12, unit: "count", threshold: 20, comparison: ">=", met: false }],
    next_eligible_at: null,
    run_id: null,
  },
  {
    operation: "expire_snapshots",
    result: "not_needed",
    measurements: [{ key: "expirable_snapshots", observed: 0, unit: "count", threshold: 1, comparison: ">=", met: false }],
    next_eligible_at: null,
    run_id: null,
  },
  { operation: "remove_orphan_files", result: "off", measurements: [], next_eligible_at: null, run_id: null },
];

function reconciliation(
  id: string,
  reconciledAt: string,
  overrides: Partial<TableReconciliationApiResponse> = {},
): TableReconciliationApiResponse {
  return {
    reconciliation_id: id,
    table_uuid: ORDERS_UUID,
    reconciled_at: reconciledAt,
    wake_reasons: { schedule: 1 },
    dry_run: false,
    outcome: "planned",
    skip_reason: null,
    operations: QUIET_OPERATIONS,
    policy_id: DEFAULT_POLICY_ID,
    policy_name: "default",
    policy_deleted: false,
    policy_version: 1,
    policy_target: null,
    ...overrides,
  };
}

export const SCHEDULED_RECONCILIATION_ID = "rc-01m72gst60f5grrcwpsxv0365q";

// Newest first, as the API returns them: a run started by catalog commits, four quiet hourly
// passes that fold into one line, a dry run that would have compacted, a paused skip, a run capped
// to 10 of 25 partitions and a compaction waiting for writes.
export const RECONCILIATIONS: TableReconciliationApiResponse[] = [
  reconciliation(SCHEDULED_RECONCILIATION_ID, "2026-11-10T10:42:00Z", {
    wake_reasons: { catalog_commit: 3 },
    policy_id: RETAIL_NIGHTLY_POLICY_ID,
    policy_name: "retail-nightly",
    policy_version: 4,
    policy_target: { type: "namespace", path: ["iceberg", "retail"] },
    operations: [
      {
        operation: "rewrite_data_files",
        result: "started",
        measurements: [
          { key: "reducible_files", observed: 1240, unit: "count", threshold: 5, comparison: ">=", met: true },
          { key: "target_file_size", observed: 134217728, unit: "bytes", threshold: null, comparison: null, met: null },
          { key: "qualifying_partitions", observed: 3, unit: "count", threshold: null, comparison: null, met: null },
        ],
        next_eligible_at: null,
        run_id: SCHEDULED_RUN_ID,
      },
      {
        operation: "rewrite_manifests",
        result: "not_needed",
        measurements: [{ key: "small_manifests", observed: 18, unit: "count", threshold: 20, comparison: ">=", met: false }],
        next_eligible_at: null,
        run_id: null,
      },
      {
        operation: "expire_snapshots",
        result: "cooling_down",
        measurements: [{ key: "expirable_snapshots", observed: 312, unit: "count", threshold: 1, comparison: ">=", met: true }],
        next_eligible_at: "2026-11-14T03:00:00Z",
        run_id: null,
      },
      { operation: "remove_orphan_files", result: "off", measurements: [], next_eligible_at: null, run_id: null },
    ],
  }),
  reconciliation("rc-01m72dbyj0estvsettdm9dkcmx", "2026-11-10T09:42:00Z"),
  reconciliation("rc-01m729y2y0ecz8089c4t29a30p", "2026-11-10T08:42:00Z"),
  reconciliation("rc-01m726g7a0e1c9rgpgzsspthwp", "2026-11-10T07:42:00Z"),
  reconciliation("rc-01m7232bp0fhwtjqjqm50mws3n", "2026-11-10T06:42:00Z"),
  reconciliation("rc-01m71zmg20etj8d09t7kday4n5", "2026-11-10T05:42:00Z", {
    dry_run: true,
    operations: [
      {
        operation: "rewrite_data_files",
        result: "would_start",
        measurements: [
          { key: "reducible_files", observed: 620, unit: "count", threshold: 5, comparison: ">=", met: true },
          { key: "target_file_size", observed: 134217728, unit: "bytes", threshold: null, comparison: null, met: null },
          { key: "qualifying_partitions", observed: 2, unit: "count", threshold: null, comparison: null, met: null },
        ],
        next_eligible_at: null,
        run_id: null,
      },
      ...QUIET_OPERATIONS.slice(1),
    ],
  }),
  reconciliation("rc-01m71w6me0ev18xh0hgdd2hvf2", "2026-11-10T04:42:00Z", {
    wake_reasons: { policy_changed: 1 },
    outcome: "skipped",
    skip_reason: "not_found",
    operations: [],
  }),
  reconciliation("rc-01m71tq3k0eq5n6a4mzv2r8b1c", "2026-11-10T03:42:00Z", {
    operations: [
      {
        operation: "rewrite_data_files",
        result: "started",
        measurements: [
          { key: "reducible_files", observed: 1240, unit: "count", threshold: 5, comparison: ">=", met: true },
          { key: "target_file_size", observed: 134217728, unit: "bytes", threshold: null, comparison: null, met: null },
          { key: "qualifying_partitions", observed: 25, unit: "count", threshold: null, comparison: null, met: null },
          { key: "selected_partitions", observed: 10, unit: "count", threshold: null, comparison: null, met: null },
          { key: "waiting_partitions", observed: 3, unit: "count", threshold: null, comparison: null, met: null },
        ],
        next_eligible_at: null,
        run_id: PARTITION_SCOPE_RUN_ID,
      },
      ...QUIET_OPERATIONS.slice(1),
    ],
  }),
  reconciliation("rc-01m71qa8d0e9w2xh7fs5tj4n6y", "2026-11-10T02:42:00Z", {
    operations: [
      {
        operation: "rewrite_data_files",
        result: "waiting_for_writes",
        measurements: [
          { key: "reducible_files", observed: 620, unit: "count", threshold: 5, comparison: ">=", met: true },
          { key: "target_file_size", observed: 134217728, unit: "bytes", threshold: null, comparison: null, met: null },
          { key: "qualifying_partitions", observed: 2, unit: "count", threshold: null, comparison: null, met: null },
          { key: "selected_partitions", observed: 0, unit: "count", threshold: null, comparison: null, met: null },
          { key: "waiting_partitions", observed: 2, unit: "count", threshold: null, comparison: null, met: null },
        ],
        next_eligible_at: "2026-11-10T02:47:00Z",
        run_id: null,
      },
      ...QUIET_OPERATIONS.slice(1),
    ],
  }),
];

// The platform default policy's content as the API returns it, the base of the policies below
// (story data only).
export const DEFAULT_POLICY_CONTENT: Required<PolicyContent> = {
  description: "",
  on: { schedule: { every_seconds: 3600 }, catalog_commit: { debounce_seconds: 300 } },
  dry_run: false,
  rewrite_data_files: {
    target: { reducible_files: { at_most: 5 }, per: "partition" },
    options: { min_input_files: 2, partial_progress_enabled: true },
  },
  rewrite_manifests: { target: { small_manifests: { at_most: 5 } }, options: null },
  expire_snapshots: { target: { min_snapshots_to_keep: 10, max_snapshot_age_seconds: 86400 }, options: null },
  remove_orphan_files: { target: { older_than_seconds: 259200 }, options: null },
};

function policy(overrides: Partial<ListedTableMaintenancePolicyApiResponse>): ListedTableMaintenancePolicyApiResponse {
  return {
    id: DEFAULT_POLICY_ID,
    name: "default",
    is_default: (overrides.id ?? DEFAULT_POLICY_ID) === DEFAULT_POLICY_ID,
    version: 1,
    attachment_count: 0,
    created_at: "2026-11-01T09:00:00Z",
    updated_at: "2026-11-01T09:00:00Z",
    ...DEFAULT_POLICY_CONTENT,
    ...overrides,
  };
}

// The default; one checked daily and not after commits, attached to a namespace and to a catalog
// that has since been dropped; and one holding only rewrite data files, in dry run, attached nowhere.
export const POLICIES: ListedTableMaintenancePolicyApiResponse[] = [
  policy({ name: "default", description: "Platform default", version: 3 }),
  policy({
    id: RETAIL_NIGHTLY_POLICY_ID,
    name: "retail-nightly",
    description: "Compacts whole tables once a day",
    version: 4,
    attachment_count: 2,
    on: { schedule: { every_seconds: 86400 }, catalog_commit: null },
    rewrite_data_files: {
      target: { reducible_files: { at_most: 20 }, per: "table" },
      options: { strategy: "sort", sort_order: "order_date DESC NULLS LAST", min_input_files: 2 },
    },
  }),
  policy({
    id: SCRATCH_POLICY_ID,
    name: "scratch",
    description: "",
    version: 1,
    dry_run: true,
    rewrite_manifests: null,
    expire_snapshots: null,
    remove_orphan_files: null,
  }),
];

// The id of retail-nightly's attachment to namespace iceberg.retail, which the mappings do not carry.
const RETAIL_NIGHTLY_ATTACHMENT_ID = "pa-01m7sd16b1ef2vww335cwcg9k8";

export const POLICY_MAPPINGS: ListedTableMaintenancePolicyMappingApiResponse[] = [
  {
    policy_id: RETAIL_NIGHTLY_POLICY_ID,
    policy_name: "retail-nightly",
    target: { type: "namespace", path: ["iceberg", "retail"], table_uuid: null },
    orphaned: false,
    attached_at: "2026-11-03T09:00:00Z",
  },
  {
    policy_id: RETAIL_NIGHTLY_POLICY_ID,
    policy_name: "retail-nightly",
    target: { type: "catalog", path: ["legacy"], table_uuid: null },
    orphaned: true,
    attached_at: "2026-11-02T09:00:00Z",
  },
];

// The targets a catalog, namespace or table takes its policies from, nearest first: the table,
// its namespaces deepest first, then the catalog.
function candidateTargets(catalog: string, namespace: string[], table?: string): string[] {
  const keys = table === undefined ? [] : [`table:${[catalog, ...namespace, table].join(".")}`];
  for (let depth = namespace.length; depth > 0; depth--) {
    keys.push(`namespace:${[catalog, ...namespace.slice(0, depth)].join(".")}`);
  }
  keys.push(`catalog:${catalog}`);
  return keys;
}

function nearest<T extends { target: PolicyTargetApiResponse }>(attachments: T[], candidates: string[]): T | undefined {
  const byTarget = new Map(attachments.map((a) => [`${a.target.type}:${a.target.path.join(".")}`, a]));
  return candidates.map((key) => byTarget.get(key)).find((a) => a !== undefined);
}

// What applies where in the story lakehouse, worked out from POLICY_MAPPINGS and
// DISCOVERY_POLICY_ATTACHMENTS as the API does: retail-nightly is attached to namespace
// iceberg.retail, core-tables to catalog iceberg and sales-tables to namespace iceberg.sales; any
// other place has the platform default of that kind.
export function effectivePolicies(catalog: string, namespace: string[] = [], table?: string): EffectivePoliciesApiResponse {
  const candidates = candidateTargets(catalog, namespace, table);
  const mapping = nearest(
    POLICY_MAPPINGS.filter((m) => !m.orphaned),
    candidates,
  );
  const maintenancePolicy = POLICIES.find((p) => p.name === (mapping?.policy_name ?? "default"))!;
  const maintenance: MaintenanceEffectivePolicyApiResponse = {
    kind: "maintenance",
    policy_id: maintenancePolicy.id,
    policy_name: maintenancePolicy.name,
    version: maintenancePolicy.version,
    description: maintenancePolicy.description,
    dry_run: maintenancePolicy.dry_run,
    target: mapping?.target ?? null,
    attachment_id: mapping === undefined ? null : RETAIL_NIGHTLY_ATTACHMENT_ID,
  };
  const attachment = nearest(
    DISCOVERY_POLICY_ATTACHMENTS.filter((a) => !a.orphaned),
    candidates,
  );
  const discoveryPolicy = attachment === undefined
    ? DEFAULT_DISCOVERY_POLICY
    : DISCOVERY_POLICIES.find((p) => p.name === attachment.policy_name)!;
  const discovery: DiscoveryEffectivePolicyApiResponse = {
    kind: "discovery",
    policy_id: discoveryPolicy.id,
    policy_name: discoveryPolicy.name,
    version: discoveryPolicy.version,
    description: discoveryPolicy.description,
    no_match_outcome: discoveryPolicy.no_match_outcome,
    target: attachment?.target ?? null,
    attachment_id: attachment?.id ?? null,
  };
  return { policies: [maintenance, discovery] };
}

function setting(
  key: string,
  label: string,
  value: number | string,
  unit: string | null,
  description: string,
): PlatformSettingApiResponse {
  return { key, label, value, unit, description };
}

function group(key: string, title: string, items: PlatformSettingApiResponse[]): PlatformSettingsGroupApiResponse {
  return { key, title, items };
}

// The platform's settings as the API words them: five groups of facts the deployment sets, with the
// values the chart defaults to.
export const PLATFORM_SETTINGS: PlatformSettingsApiResponse = {
  groups: [
    group("execution_capacity", "Execution capacity", [
      setting("maintenance_attempt_deadline_seconds", "Attempt time limit", 21600, "seconds",
        "How long one attempt may run once its Spark job has started; time spent waiting in the queue does not count."),
      setting("maintenance_queue_wait_limit_seconds", "Queue wait limit", 86400, "seconds",
        "How long one attempt may wait in its Volcano queue before it is stopped; its operation then waits for the next plan."),
      setting("maintenance_max_attempts", "Attempts per operation", 3, "attempts",
        "How many times one run tries an operation before it gives the operation up as failed."),
    ]),
    group("compute_sizes", "Spark sizes", [
      setting("compute_size_s_driver_memory", "S driver memory", "768m", null,
        "The memory of the Spark driver when an operation runs at size S."),
      setting("compute_size_s_executor_memory", "S executor memory", "768m", null,
        "The memory of each Spark executor when an operation runs at size S."),
      setting("compute_size_s_executor_instances", "S executors", 1, "executors",
        "How many Spark executors an operation gets when it runs at size S."),
      setting("compute_size_m_driver_memory", "M driver memory", "1g", null,
        "The memory of the Spark driver when an operation runs at size M."),
      setting("compute_size_m_executor_memory", "M executor memory", "1536m", null,
        "The memory of each Spark executor when an operation runs at size M."),
      setting("compute_size_m_executor_instances", "M executors", 1, "executors",
        "How many Spark executors an operation gets when it runs at size M."),
      setting("compute_size_l_driver_memory", "L driver memory", "1536m", null,
        "The memory of the Spark driver when an operation runs at size L."),
      setting("compute_size_l_executor_memory", "L executor memory", "2g", null,
        "The memory of each Spark executor when an operation runs at size L."),
      setting("compute_size_l_executor_instances", "L executors", 1, "executors",
        "How many Spark executors an operation gets when it runs at size L."),
    ]),
    group("cooldown_and_backoff", "Cooldown and backoff", [
      setting("maintenance_rewrite_data_files_cooldown_seconds", "Rewrite data files cooldown", 3600, "seconds",
        "The least time between two runs of rewrite data files on one table."),
      setting("maintenance_rewrite_manifests_cooldown_seconds", "Rewrite manifests cooldown", 21600, "seconds",
        "The least time between two runs of rewrite manifests on one table."),
      setting("maintenance_expire_snapshots_cooldown_seconds", "Expire snapshots cooldown", 21600, "seconds",
        "The least time between two runs of expire snapshots on one table."),
      setting("maintenance_remove_orphan_files_interval_seconds", "Orphan file removal interval", 604800, "seconds",
        "How often orphan files are removed from a table: they have no target the platform can measure."),
      setting("maintenance_failure_backoff_cap_seconds", "Failure backoff cap", 86400, "seconds",
        "Each failure of an operation doubles its cooldown, up to this limit."),
    ]),
    group("partition_selection", "Compaction partition selection", [
      setting("maintenance_compaction_partitions_per_job", "Partitions per job", 10, "partitions",
        "The most partitions one rewrite data files job compacts; those over the target for the longest wait go first, oldest first, then the ones with the most reducible files; the rest wait for a later check."),
      setting("maintenance_compaction_quiet_seconds", "Quiet period", 120, "seconds",
        "A partition written more recently than this waits for a later check, so compaction does not race its writers."),
      setting("maintenance_compaction_max_quiet_wait_seconds", "Longest wait for quiet", 3600, "seconds",
        "A partition over its target for this long is compacted even while it is still being written."),
    ]),
    group("discovery", "Discovery", [
      setting("discovery_interval_seconds", "Scan interval", 600, "seconds",
        "How often discovery scans the catalogs for tables to manage."),
    ]),
  ],
};

const METRICS_END = Date.parse("2026-11-20T10:00:00Z");
const METRICS_STEP_SECONDS = 180;
const METRICS_STEPS = 120;
const COMPACTED_AT_STEP = 80;

// orders over six hours, one value every three minutes: files, deletes, reducible files and manifests
// pile up until a compaction at step 80 folds them, while rows and size keep growing.
function ordersMetricsAt(step: number): TableMetricValuesApiResponse {
  const since = step - COMPACTED_AT_STEP;
  const compacted = since >= 0;
  const dataFiles = compacted ? 1150 + Math.round(since * 0.6) : 1100 + step * 4;
  const manifests = compacted ? 6 + Math.floor(since / 14) : 8 + Math.floor(step / 6);
  return {
    data_files: dataFiles,
    position_delete_files: compacted ? Math.floor(since / 10) : 10 + Math.floor(step / 4),
    equality_delete_files: compacted ? 0 : 2 + Math.floor(step / 30),
    deletion_vectors: compacted ? 0 : Math.floor(step / 20),
    data_records: 48_200_000 + step * 90_000,
    position_delete_records: compacted ? since * 12 : 400 + step * 35,
    equality_delete_records: compacted ? 0 : 20 + step * 3,
    data_size_bytes: 3_435_973_837 + step * 7_340_032,
    reducible_files: compacted ? 12 + Math.floor(since / 4) : 180 + step * 3,
    snapshots: compacted ? 14 + Math.floor(since / 8) : 20 + Math.floor(step / 4),
    manifests,
    manifests_size_bytes: manifests * 49_152,
    manifest_added_entries: 4,
    manifest_existing_entries: dataFiles,
    manifest_deleted_entries: 0,
  };
}

function metricsAt(step: number): string {
  return new Date(METRICS_END - (METRICS_STEPS - step) * METRICS_STEP_SECONDS * 1000).toISOString();
}

export const ORDERS_CURRENT_METRICS: TableCurrentMetricsApiResponse = {
  observed_at: "2026-11-20T09:58:00Z",
  metrics: ordersMetricsAt(METRICS_STEPS),
};

// The last six hours as the API sends them: Prometheus started a little after the window began, so the
// first points are gaps, and it missed one scrape at step 50.
export const ORDERS_METRIC_TRENDS: TableMetricTrendsApiResponse = {
  time_range: "6h",
  start: metricsAt(0),
  end: metricsAt(METRICS_STEPS),
  step_seconds: METRICS_STEP_SECONDS,
  points: Array.from({ length: METRICS_STEPS + 1 }, (_, step) => {
    const metrics = ordersMetricsAt(step);
    const entries = metrics.manifest_added_entries + metrics.manifest_existing_entries + metrics.manifest_deleted_entries;
    const values = {
      ...metrics,
      manifest_average_size_bytes: metrics.manifests_size_bytes / metrics.manifests,
      manifest_average_entries: entries / metrics.manifests,
    };
    const gap = step < 6 || step === 50;
    return {
      at: metricsAt(step),
      values: Object.fromEntries(Object.entries(values).map(([key, value]) => [key, gap ? null : value])),
    };
  }),
};
