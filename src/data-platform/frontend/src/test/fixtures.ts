import type { TableApiResponse } from "../api/generated/model";

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
