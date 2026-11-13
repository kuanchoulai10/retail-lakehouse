import type {
  ApplicableTableMaintenancePolicyApiResponse,
  CatalogApiResponse,
  CatalogTableApiResponse,
  CompactionCandidateApiResponse,
  CompactionCandidatesApiResponse,
  CompactionRoundApiResponse,
  ListedTableMaintenancePolicyApiResponse,
  ListedTableMaintenancePolicyMappingApiResponse,
  NamespaceApiResponse,
  NamespaceSummaryApiResponse,
  ReconciliationOperationApiResponse,
  TableApiResponse,
  TableCommitsApiResponse,
  PreviewTableDiscoveryRulesApiResponse,
  TableDiscoveryRuleApiResponse,
  TableHealthApiResponse,
  TableIdentifierApiResponse,
  TableMaintenanceRunApiResponse,
  TableReconciliationApiResponse,
  TableStorageApiResponse,
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
  status: "managed",
  matched_rule_id: "rule-retail",
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
    status: "unmanaged",
    matched_rule_id: null,
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
        attempt_history: [
          {
            attempt: 1,
            size: "S",
            status: "succeeded",
            started_at: "2026-11-08T02:00:00Z",
            finished_at: "2026-11-08T02:03:10Z",
            failure_class: null,
            error: null,
            event_log_finished: true,
            next_step: "done",
            next_size: null,
          },
        ],
      },
    ],
  },
];

// A compaction that ran out of memory at S and succeeded at M.
export const ESCALATED_RUN: TableMaintenanceRunApiResponse = {
  run_id: "run-escalated",
  table_uuid: ORDERS_UUID,
  execution_ref: `table-maintenance:table=${ORDERS_UUID}:run=run-escalated`,
  trigger: "manual",
  status: "succeeded",
  created_at: "2026-11-09T02:00:00Z",
  finished_at: "2026-11-09T02:09:40Z",
  operations: [
    {
      operation: "rewrite_data_files",
      status: "succeeded",
      attempts: 2,
      started_at: "2026-11-09T02:03:20Z",
      finished_at: "2026-11-09T02:09:40Z",
      job_name: "tm-orders-rewrite-2",
      metrics: { rewritten_data_files_count: 24, peak_driver_heap_bytes: 612368384, peak_executor_heap_bytes: 1140850688 },
      error: null,
      expected_files: null,
      attempt_history: [
        {
          attempt: 1,
          size: "S",
          status: "failed",
          started_at: "2026-11-09T02:00:00Z",
          finished_at: "2026-11-09T02:02:10Z",
          failure_class: "oom",
          error: "Py4JJavaError: An error occurred while calling o61.sql. java.lang.OutOfMemoryError: Java heap space",
          event_log_finished: false,
          next_step: "retry_larger",
          next_size: "M",
        },
        {
          attempt: 2,
          size: "M",
          status: "succeeded",
          started_at: "2026-11-09T02:03:20Z",
          finished_at: "2026-11-09T02:09:40Z",
          failure_class: null,
          error: null,
          event_log_finished: true,
          next_step: "done",
          next_size: null,
        },
      ],
    },
  ],
};

const ROUND_ID = "compaction-rounds-2026-11-13T02:00:00Z";

function orderDay(day: string, overrides: Partial<CompactionCandidateApiResponse>): CompactionCandidateApiResponse {
  return {
    partition: { spec_id: 0, values: [day] },
    partition_label: `ordered_at_day=${day}`,
    state: "pending",
    hold_reason: null,
    reducible_files: 18,
    data_bytes: 96 * 1024 * 1024,
    estimated_gb_hours: 0.12,
    score: 0.5,
    rank: null,
    claimed_by_run_id: null,
    lease_expires_at: null,
    last_written_at: "2026-11-12T23:40:00Z",
    observed_at: "2026-11-13T02:00:00Z",
    priority: "P0",
    granted_round_id: null,
    pending_since: null,
    overdue: false,
    ...overrides,
  };
}

// The order days that need compaction, best first: one in a run, one still being written, one a
// round granted, the top two pending (two per run, one overdue), one below them and one too small.
export const CANDIDATES: CompactionCandidatesApiResponse = {
  partitions_per_run: 2,
  candidates: [
    orderDay("2026-11-10", {
      state: "running",
      score: 0.92,
      reducible_files: 412,
      data_bytes: 1_932_735_283,
      estimated_gb_hours: 0.9,
      claimed_by_run_id: "run-1",
      lease_expires_at: "2026-11-13T21:48:00Z",
    }),
    orderDay("2026-11-12", {
      state: "held",
      hold_reason: "recently_written",
      score: 0.81,
      reducible_files: 240,
      last_written_at: "2026-11-13T01:59:00Z",
    }),
    orderDay("2026-11-09", {
      state: "granted",
      score: 0.74,
      reducible_files: 160,
      data_bytes: 640 * 1024 * 1024,
      estimated_gb_hours: 0.35,
      granted_round_id: ROUND_ID,
      lease_expires_at: "2026-11-13T02:10:00Z",
      pending_since: "2026-11-13T01:00:00Z",
    }),
    orderDay("2026-11-08", { rank: 1, score: 0.55, reducible_files: 96, pending_since: "2026-11-12T22:00:00Z", overdue: true }),
    orderDay("2026-11-07", { rank: 2, score: 0.31, reducible_files: 40, pending_since: "2026-11-13T01:00:00Z" }),
    orderDay("2026-11-05", { rank: 3, score: 0.22, reducible_files: 24, pending_since: "2026-11-13T01:00:00Z" }),
    orderDay("2026-11-06", { state: "held", hold_reason: "too_small", score: 0.08, reducible_files: 6, data_bytes: 2 * 1024 * 1024, estimated_gb_hours: 0.01 }),
  ],
};

export const RULES: TableDiscoveryRuleApiResponse[] = [
  {
    id: "rule-retail",
    priority: 10,
    action: "include",
    catalogs: ["iceberg"],
    namespaces: ["retail"],
    tables: ["*"],
    enabled: true,
    created_at: "2026-11-01T09:00:00Z",
    updated_at: "2026-11-01T09:00:00Z",
  },
  {
    id: "rule-tmp",
    priority: 50,
    action: "exclude",
    catalogs: ["*"],
    namespaces: ["*"],
    tables: ["tmp_*", "staging_*"],
    enabled: false,
    created_at: "2026-11-01T09:00:00Z",
    updated_at: "2026-11-01T09:00:00Z",
  },
];

// What the rules above decide: the retail rule manages both retail tables; nothing matches staging.
export const RULES_PREVIEW: PreviewTableDiscoveryRulesApiResponse = {
  tables: [
    { catalog: "iceberg", namespace: "retail", table: "orders", rule_id: "rule-retail", managed: true },
    { catalog: "iceberg", namespace: "retail", table: "customers", rule_id: "rule-retail", managed: true },
    { catalog: "iceberg", namespace: "staging", table: "tmp_events", rule_id: null, managed: false },
  ],
  managed: 2,
  unmanaged: 1,
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
  },
  {
    operation: "rewrite_manifests",
    result: "not_needed",
    measurements: [{ key: "small_manifests", observed: 12, unit: "count", threshold: 20, comparison: ">=", met: false }],
    next_eligible_at: null,
  },
  {
    operation: "expire_snapshots",
    result: "not_needed",
    measurements: [{ key: "expirable_snapshots", observed: 0, unit: "count", threshold: 1, comparison: ">=", met: false }],
    next_eligible_at: null,
  },
  { operation: "remove_orphan_files", result: "off", measurements: [], next_eligible_at: null },
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
    run_id: null,
    policy_name: "default",
    policy_version: 1,
    policy_target: null,
    ...overrides,
  };
}

// Newest first, as the API returns them: a run started by catalog commits, four quiet hourly
// passes that fold into one line, a dry run that would have compacted, and a paused skip.
export const RECONCILIATIONS: TableReconciliationApiResponse[] = [
  reconciliation("rec-109", "2026-11-10T10:42:00Z", {
    wake_reasons: { catalog_commit: 3 },
    policy_name: "retail-nightly",
    policy_version: 4,
    policy_target: { type: "namespace", path: ["iceberg", "retail"] },
    run_id: "run-1",
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
      },
      {
        operation: "rewrite_manifests",
        result: "not_needed",
        measurements: [{ key: "small_manifests", observed: 18, unit: "count", threshold: 20, comparison: ">=", met: false }],
        next_eligible_at: null,
      },
      {
        operation: "expire_snapshots",
        result: "cooling_down",
        measurements: [{ key: "expirable_snapshots", observed: 312, unit: "count", threshold: 1, comparison: ">=", met: true }],
        next_eligible_at: "2026-11-14T03:00:00Z",
      },
      { operation: "remove_orphan_files", result: "off", measurements: [], next_eligible_at: null },
    ],
  }),
  reconciliation("rec-108", "2026-11-10T09:42:00Z"),
  reconciliation("rec-107", "2026-11-10T08:42:00Z"),
  reconciliation("rec-106", "2026-11-10T07:42:00Z"),
  reconciliation("rec-105", "2026-11-10T06:42:00Z"),
  reconciliation("rec-104", "2026-11-10T05:42:00Z", {
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
      },
      ...QUIET_OPERATIONS.slice(1),
    ],
  }),
  reconciliation("rec-103", "2026-11-10T04:42:00Z", {
    wake_reasons: { policy_changed: 1 },
    outcome: "skipped",
    skip_reason: "not_found",
    operations: [],
  }),
];

// The spec's default policy content, the base of the policies below (story data only).
export const DEFAULT_POLICY_CONTENT: PolicyContent = {
  description: "",
  reconcile_interval_seconds: 3600,
  dry_run: false,
  priority: "P2",
  operations: {
    rewrite_data_files: {
      enabled: true,
      scope: { unit: "partition" },
      trigger_policy: { cooldown_seconds: 3600, conditions: { reducible_files: { at_least: 5 } } },
      execution_policy: { target_file_size_bytes: null, min_input_files: 2, partial_progress: { enabled: true, max_commits: null } },
    },
    rewrite_manifests: {
      enabled: true,
      trigger_policy: { cooldown_seconds: 21600, conditions: { small_manifests: { at_least: 5, smaller_than_bytes: null } } },
      execution_policy: {},
    },
    expire_snapshots: {
      enabled: true,
      trigger_policy: { cooldown_seconds: 21600, conditions: { expirable_snapshots: { at_least: 1 } } },
      execution_policy: { older_than_seconds: 86400, retain_last: 10 },
    },
    remove_orphan_files: {
      enabled: true,
      trigger_policy: { cooldown_seconds: 604800, conditions: {} },
      execution_policy: { older_than_seconds: 259200 },
    },
  },
};

function policy(overrides: Partial<ListedTableMaintenancePolicyApiResponse>): ListedTableMaintenancePolicyApiResponse {
  return {
    name: "default",
    version: 1,
    attachment_count: 0,
    created_at: "2026-11-01T09:00:00Z",
    updated_at: "2026-11-01T09:00:00Z",
    ...DEFAULT_POLICY_CONTENT,
    priority: DEFAULT_POLICY_CONTENT.priority ?? "P2",
    ...overrides,
  };
}

// The default, one policy attached to a namespace and to a catalog that has since been
// dropped, and one attached nowhere.
export const POLICIES: ListedTableMaintenancePolicyApiResponse[] = [
  policy({ name: "default", description: "Platform default", version: 3 }),
  policy({
    name: "retail-nightly",
    description: "Compacts whole tables once a day",
    version: 4,
    attachment_count: 2,
    reconcile_interval_seconds: 86400,
    priority: "P0",
    operations: {
      ...DEFAULT_POLICY_CONTENT.operations,
      rewrite_data_files: {
        ...DEFAULT_POLICY_CONTENT.operations.rewrite_data_files,
        scope: { unit: "table" },
        trigger_policy: { cooldown_seconds: 86400, conditions: { reducible_files: { at_least: 20 } } },
      },
    },
  }),
  policy({ name: "scratch", description: "", version: 1, dry_run: true }),
];

export const POLICY_MAPPINGS: ListedTableMaintenancePolicyMappingApiResponse[] = [
  {
    policy_name: "retail-nightly",
    target: { type: "namespace", path: ["iceberg", "retail"], table_uuid: null },
    orphaned: false,
    attached_at: "2026-11-03T09:00:00Z",
  },
  {
    policy_name: "retail-nightly",
    target: { type: "catalog", path: ["legacy"], table_uuid: null },
    orphaned: true,
    attached_at: "2026-11-02T09:00:00Z",
  },
];

const RETAIL_TARGET = { type: "namespace", path: ["iceberg", "retail"], table_uuid: null };

// What applies where in the story lakehouse: retail-nightly is attached to namespace retail
// (POLICY_MAPPINGS), so the namespace has it attached, its tables inherit it, and the catalog
// falls back to the platform default.
export function applicablePolicy(catalog: string, namespace: string[] = []): ApplicableTableMaintenancePolicyApiResponse {
  const inRetail = catalog === "iceberg" && namespace[0] === "retail";
  return { ...POLICIES[inRetail ? 1 : 0]!, target: inRetail ? RETAIL_TARGET : null };
}

// Two rounds of the compaction scheduler: the newest granted an order day (P0, weight 4) and a
// stock-levels partition, then ran out of budget; the one before had nothing pending.
export const ROUNDS: CompactionRoundApiResponse[] = [
  {
    round_id: ROUND_ID,
    started_at: "2026-11-13T02:00:00Z",
    budget_gb_hours: 0.5,
    used_gb_hours: 0.47,
    picks: [
      {
        table_uuid: ORDERS_UUID,
        table_name: "iceberg.retail.orders",
        partition: { spec_id: 0, values: ["2026-11-09"] },
        partition_label: "ordered_at_day=2026-11-09",
        priority: "P0",
        score: 0.74,
        weighted_score: 2.96,
        estimated_gb_hours: 0.35,
        overdue: false,
      },
      {
        table_uuid: "1d3f5b7a-2c4e-4a6b-8c0d-e2f4a6b8c0d1",
        table_name: "iceberg.inventory.stock_levels",
        partition: { spec_id: 0, values: ["2026-11-12"] },
        partition_label: "updated_at_day=2026-11-12",
        priority: "P2",
        score: 0.81,
        weighted_score: 0.81,
        estimated_gb_hours: 0.12,
        overdue: false,
      },
    ],
    skips: [
      {
        table_uuid: ORDERS_UUID,
        table_name: "iceberg.retail.orders",
        partition: { spec_id: 0, values: ["2026-11-08"] },
        partition_label: "ordered_at_day=2026-11-08",
        priority: "P0",
        score: 0.55,
        weighted_score: 2.2,
        estimated_gb_hours: 0.12,
        overdue: true,
        reason: "budget_used",
      },
    ],
    skipped_total: 4,
  },
  {
    round_id: "compaction-rounds-2026-11-13T01:58:00Z",
    started_at: "2026-11-13T01:58:00Z",
    budget_gb_hours: 0.5,
    used_gb_hours: 0,
    picks: [],
    skips: [],
    skipped_total: 0,
  },
];
