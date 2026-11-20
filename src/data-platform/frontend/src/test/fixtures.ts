import type {
  CreateTableMaintenancePolicyApiRequest,
  ListedTableMaintenancePolicyApiResponse,
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
    priority: "P3",
    matched_rule_id: "dr-01m7s6c3tqee0rhg00xn5s97gw",
    operation_states: {},
    registered_at: "2026-10-30T10:00:00Z",
    updated_at: "2026-10-31T08:00:00Z",
    last_committed_at: "2026-10-31T07:45:00Z",
    last_discovered_at: "2026-10-31T08:10:00Z",
    ...overrides,
  };
}

// The platform default policy's content, as the API returns it (every block and option key
// present or null).
export function policyContentFixture(): Required<Omit<CreateTableMaintenancePolicyApiRequest, "name">> {
  return {
    description: "Platform default",
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
}

// Policy ids: the default's fixed id and one for each other policy the tests name.
export const DEFAULT_POLICY_ID = "mp-00000000000000000000000000";
export const NIGHTLY_POLICY_ID = "mp-01m7sd16b1ef2vww335cwcg9k7";
export const SCRATCH_POLICY_ID = "mp-01m7sd16b1ef2vww335jk8dm9t";

export function policyFixture(
  overrides: Partial<ListedTableMaintenancePolicyApiResponse> = {},
): ListedTableMaintenancePolicyApiResponse {
  return {
    id: DEFAULT_POLICY_ID,
    name: "default",
    // As the backend tells it: the default is the policy with the fixed id.
    is_default: (overrides.id ?? DEFAULT_POLICY_ID) === DEFAULT_POLICY_ID,
    version: 3,
    attachment_count: 0,
    created_at: "2026-11-01T09:00:00Z",
    updated_at: "2026-11-02T09:00:00Z",
    ...policyContentFixture(),
    ...overrides,
  };
}
