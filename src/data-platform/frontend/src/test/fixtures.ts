import type {
  CreateTableMaintenancePolicyApiRequest,
  ListedTableMaintenancePolicyApiResponse,
  SchedulerSettingsApiResponse,
  TableApiResponse,
} from "../api/generated/model";

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
    status: "managed",
    matched_rule_id: "rule-1",
    operation_states: {},
    registered_at: "2026-10-30T10:00:00Z",
    updated_at: "2026-10-31T08:00:00Z",
    ...overrides,
  };
}

// The platform default policy's content, as the spec gives it.
export function policyContentFixture(): Omit<CreateTableMaintenancePolicyApiRequest, "name"> {
  return {
    description: "Platform default",
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
}

export function policyFixture(
  overrides: Partial<ListedTableMaintenancePolicyApiResponse> = {},
): ListedTableMaintenancePolicyApiResponse {
  return {
    name: "default",
    version: 3,
    attachment_count: 0,
    created_at: "2026-11-01T09:00:00Z",
    updated_at: "2026-11-02T09:00:00Z",
    ...policyContentFixture(),
    priority: "P2",
    ...overrides,
  };
}

// The scheduler's defaults: P0 within 1 h, P1 within 4 h, P2 within 8 h.
export const SCHEDULER_SETTINGS: SchedulerSettingsApiResponse = {
  round_seconds: 120,
  budget_gb_hours: 0.05,
  grant_lease_seconds: 600,
  priorities: [
    { priority: "P0", weight: 4, sla_seconds: 3600 },
    { priority: "P1", weight: 2, sla_seconds: 14_400 },
    { priority: "P2", weight: 1, sla_seconds: 28_800 },
  ],
};
