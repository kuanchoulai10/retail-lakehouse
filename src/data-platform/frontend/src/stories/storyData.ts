import type {
  ApplicableTableMaintenancePolicyApiResponse,
  CatalogApiResponse,
  CatalogTableApiResponse,
  CatalogTablePropertiesApiResponse,
  CompactionCandidateApiResponse,
  CompactionCandidatesApiResponse,
  CompactionRoundApiResponse,
  ListedTableMaintenancePolicyApiResponse,
  ListedTableMaintenancePolicyMappingApiResponse,
  NamespaceApiResponse,
  NamespaceSummaryApiResponse,
  PlatformSettingApiResponse,
  PlatformSettingsApiResponse,
  PlatformSettingsGroupApiResponse,
  ReconciliationOperationApiResponse,
  SchedulerSettingsApiResponse,
  TableApiResponse,
  TableCommitsApiResponse,
  TableDiscoveryRuleApiResponse,
  TableIdentifierApiResponse,
  TableMaintenanceRunApiResponse,
  TableMaintenanceRunAttemptApiResponse,
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
  matched_rule_id: "dr-01m7s6c3tqee0rhg00xry2zqqt",
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

export const SCHEDULED_RUN_ID = "mr-01m6we4j80f049yj9fq93t3z57";
export const ESCALATED_RUN_ID = "mr-01m6z0h980ebq90tzxr5xezxae";

export const RUNS: TableMaintenanceRunApiResponse[] = [
  {
    run_id: SCHEDULED_RUN_ID,
    table_uuid: ORDERS_UUID,
    execution_ref: `table-maintenance:table-uuid=${ORDERS_UUID}`,
    trigger: "scheduled",
    priority: "P3",
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
            started_running_at: "2026-11-08T02:00:00Z",
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
  run_id: ESCALATED_RUN_ID,
  table_uuid: ORDERS_UUID,
  execution_ref: `table-maintenance:table-uuid=${ORDERS_UUID}`,
  trigger: "manual",
  priority: "P3",
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
          started_running_at: "2026-11-09T02:00:00Z",
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
          started_running_at: "2026-11-09T02:03:20Z",
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

export const IN_FLIGHT_RUN_ID = "mr-01m7bk4q80f3dt6ywe2m5c1h9a";
export const QUEUE_TIMEOUT_RUN_ID = "mr-01m7bk9d30ff8e5hn7a2xk4b6c";
const MINUTE_MS = 60_000;

type Attempt = TableMaintenanceRunAttemptApiResponse;

function runOfAttempts(
  runId: string,
  status: string,
  attempts: Attempt[],
  finishedAt: string | null,
): TableMaintenanceRunApiResponse {
  return {
    run_id: runId,
    table_uuid: ORDERS_UUID,
    execution_ref: `table-maintenance:table-uuid=${ORDERS_UUID}`,
    trigger: "manual",
    priority: "P1",
    status,
    created_at: attempts[0]!.started_at,
    finished_at: finishedAt,
    operations: [
      {
        operation: "rewrite_data_files",
        status,
        attempts: attempts.length,
        started_at: attempts[0]!.started_at,
        finished_at: finishedAt,
        job_name: "tm-orders-rewrite-live",
        metrics: {},
        error: null,
        expected_files: null,
        attempt_history: attempts,
      },
    ],
  };
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
    }),
  ],
  "2026-11-19T02:00:00Z",
);

export const NEWEST_ROUND_ID = "cr-01m79a4580ekrvn7jjtkvbg2gx";
const OLDER_ROUND_ID = "cr-01m79a0g20fyg9rjvt5yegdse3";

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
    granted_round_started_at: null,
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
      claimed_by_run_id: SCHEDULED_RUN_ID,
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
      granted_round_id: NEWEST_ROUND_ID,
      granted_round_started_at: "2026-11-13T02:00:00Z",
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
    id: "dr-01m7s6c3tqee0rhg00xry2zqqt",
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
    id: "dr-01m7s6c3tqee0rhg00xz1dk9cs",
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
    policy_id: DEFAULT_POLICY_ID,
    policy_name: "default",
    policy_deleted: false,
    policy_version: 1,
    policy_target: null,
    ...overrides,
  };
}

// Newest first, as the API returns them: a run started by catalog commits, four quiet hourly
// passes that fold into one line, a dry run that would have compacted, and a paused skip.
export const RECONCILIATIONS: TableReconciliationApiResponse[] = [
  reconciliation("rc-01m72gst60f5grrcwpsxv0365q", "2026-11-10T10:42:00Z", {
    wake_reasons: { catalog_commit: 3 },
    policy_id: RETAIL_NIGHTLY_POLICY_ID,
    policy_name: "retail-nightly",
    policy_version: 4,
    policy_target: { type: "namespace", path: ["iceberg", "retail"] },
    run_id: SCHEDULED_RUN_ID,
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
    id: DEFAULT_POLICY_ID,
    name: "default",
    is_default: (overrides.id ?? DEFAULT_POLICY_ID) === DEFAULT_POLICY_ID,
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
    id: RETAIL_NIGHTLY_POLICY_ID,
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
  policy({ id: SCRATCH_POLICY_ID, name: "scratch", description: "", version: 1, dry_run: true }),
];

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

const RETAIL_TARGET = { type: "namespace", path: ["iceberg", "retail"], table_uuid: null };

// What applies where in the story lakehouse: retail-nightly is attached to namespace retail
// (POLICY_MAPPINGS), so the namespace has it attached, its tables inherit it, and the catalog
// falls back to the platform default.
export function applicablePolicy(catalog: string, namespace: string[] = []): ApplicableTableMaintenancePolicyApiResponse {
  const inRetail = catalog === "iceberg" && namespace[0] === "retail";
  return { ...POLICIES[inRetail ? 1 : 0]!, target: inRetail ? RETAIL_TARGET : null };
}

// The scheduler's settings: a round every 2 minutes within 0.5 GB·h, and each priority's weight and
// the time it allows a pending partition before it is overdue.
export const SCHEDULER_SETTINGS: SchedulerSettingsApiResponse = {
  round_seconds: 120,
  budget_gb_hours: 0.5,
  grant_lease_seconds: 600,
  priorities: [
    { priority: "P0", weight: 4, sla_seconds: 3600 },
    { priority: "P1", weight: 2, sla_seconds: 14_400 },
    { priority: "P2", weight: 1, sla_seconds: 28_800 },
  ],
};

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
      setting("admission_limit", "Concurrent operations", 2, "operations",
        "How many maintenance operations may run at the same time across the whole platform."),
      setting("maintenance_attempt_deadline_seconds", "Attempt time limit", 21600, "seconds",
        "How long one attempt of an operation may run before it is stopped and counted as failed."),
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
    group("compaction_scheduling", "Compaction scheduling", [
      setting("scheduler_round_seconds", "Round interval", 120, "seconds",
        "How often a compaction round decides which partitions to compact next."),
      setting("scheduler_budget_gb_hours", "Round budget", 0.05, "GB·hours",
        "The most estimated compute a single round may grant, in GB·hours."),
      setting("scheduler_priority_weight_p0", "P0 weight", 4, "times",
        "How many times a P0 partition's score is multiplied when a round ranks partitions."),
      setting("scheduler_priority_weight_p1", "P1 weight", 2, "times",
        "How many times a P1 partition's score is multiplied when a round ranks partitions."),
      setting("scheduler_priority_weight_p2", "P2 weight", 1, "times",
        "How many times a P2 partition's score is multiplied when a round ranks partitions."),
      setting("scheduler_sla_seconds_p0", "P0 SLA", 3600, "seconds",
        "How long a P0 partition may wait for compaction before it is shown as overdue."),
      setting("scheduler_sla_seconds_p1", "P1 SLA", 14400, "seconds",
        "How long a P1 partition may wait for compaction before it is shown as overdue."),
      setting("scheduler_sla_seconds_p2", "P2 SLA", 28800, "seconds",
        "How long a P2 partition may wait for compaction before it is shown as overdue."),
      setting("scheduler_grant_lease_seconds", "Grant retention", 600, "seconds",
        "How long a granted partition stays reserved for its table to claim before the grant lapses."),
      setting("compaction_partitions_per_run", "Partitions per run", 10, "partitions",
        "The most partitions one compaction run rewrites."),
      setting("compaction_quiet_seconds", "Quiet period", 120, "seconds",
        "How long a partition must go without a new write before it is compacted."),
      setting("compaction_max_quiet_wait_seconds", "Longest quiet wait", 3600, "seconds",
        "The longest a partition that keeps receiving writes is held back before it is compacted anyway."),
      setting("compaction_min_partition_bytes", "Minimum partition size", 0, "bytes",
        "A partition with less data than this is left alone as too small to compact."),
    ]),
    group("cooldown_and_backoff", "Cooldown and backoff", [
      setting("maintenance_failure_backoff_cap_seconds", "Failure backoff cap", 86400, "seconds",
        "Each failure of an operation doubles its cooldown, up to this limit."),
    ]),
    group("discovery", "Discovery", [
      setting("discovery_interval_seconds", "Scan interval", 600, "seconds",
        "How often discovery scans the catalogs for tables to manage."),
    ]),
  ],
};

// Two rounds of the compaction scheduler: the newest granted an order day (P0, weight 4) and a
// stock-levels partition, then ran out of budget; the one before had nothing pending.
export const ROUNDS: CompactionRoundApiResponse[] = [
  {
    round_id: NEWEST_ROUND_ID,
    started_at: "2026-11-13T02:00:00Z",
    budget_gb_hours: 0.5,
    used_gb_hours: 0.47,
    picks: [
      {
        table_uuid: ORDERS_UUID,
        table_name: "iceberg.retail.orders",
        table: { catalog: "iceberg", namespace: ["retail"], name: "orders" },
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
        table: { catalog: "iceberg", namespace: ["inventory"], name: "stock_levels" },
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
        table: { catalog: "iceberg", namespace: ["retail"], name: "orders" },
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
    busy_skipped: 3,
  },
  {
    round_id: OLDER_ROUND_ID,
    started_at: "2026-11-13T01:58:00Z",
    budget_gb_hours: 0.5,
    used_gb_hours: 0,
    picks: [],
    skips: [],
    skipped_total: 0,
    busy_skipped: 0,
  },
];
