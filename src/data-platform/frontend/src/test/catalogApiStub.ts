import { http } from "msw";
import type {
  CatalogApiResponse,
  CatalogTableApiResponse,
  CatalogTablePropertiesApiResponse,
  CatalogTablePropertyApiResponse,
} from "../api/generated/model";
import { jsonResponse } from "./fixtures";
import { server } from "./mswServer";

// A promise lets a test hold the response back (one that never settles keeps the query loading).
export type StubHandler = (body: unknown) => Response | Promise<Response>;

export interface StubbedCall {
  method: string;
  path: string;
  body: unknown;
}

// A key ending in "*" matches every request that starts with the text before it.
function prefixHandler(routes: Record<string, StubHandler>, request: string): StubHandler | undefined {
  const key = Object.keys(routes).find((k) => k.endsWith("*") && request.startsWith(k.slice(0, -1)));
  return key === undefined ? undefined : routes[key];
}

// Answers API requests with handlers keyed "METHOD /v1/path?query" (the /console/api prefix is dropped),
// through the MSW server, so the app's real fetch runs. An unstubbed request answers 500, so a test sees it
// instead of hanging.
export function stubCatalogApi(routes: Record<string, StubHandler>): StubbedCall[] {
  const calls: StubbedCall[] = [];
  server.use(
    http.all("/console/api/*", async ({ request }) => {
      const url = new URL(request.url);
      const path = `${url.pathname.replace(/^\/console\/api/, "")}${url.search}`;
      const text = await request.text();
      const body = text === "" ? undefined : (JSON.parse(text) as unknown);
      calls.push({ method: request.method, path, body });
      const key = `${request.method} ${path}`;
      const handler = routes[key] ?? prefixHandler(routes, key);
      if (handler === undefined) {
        return jsonResponse({ detail: `no stub for ${key}` }, 500);
      }
      return handler(body);
    }),
  );
  return calls;
}

export function callsTo(calls: StubbedCall[], method: string, path: string): StubbedCall[] {
  return calls.filter((call) => call.method === method && call.path === path);
}

export function catalogFixture(overrides: Partial<CatalogApiResponse> = {}): CatalogApiResponse {
  return {
    name: "iceberg",
    type: "INTERNAL",
    default_base_location: "s3://warehouse/iceberg",
    properties: { "default-base-location": "s3://warehouse/iceberg", owner: "data" },
    storage_config: {
      storage_type: "S3",
      allowed_locations: ["s3://warehouse/iceberg/"],
      region: "us-east-1",
      role_arn: null,
      external_id: null,
      user_arn: null,
      endpoint: "http://rustfs:9000",
      endpoint_internal: null,
      sts_endpoint: null,
      sts_unavailable: true,
      path_style_access: true,
      tenant_id: null,
      multi_tenant_app_name: null,
      consent_url: null,
      gcs_service_account: null,
    },
    connection_config: null,
    entity_version: 7,
    created_at: "2026-11-01T10:00:00Z",
    updated_at: "2026-11-02T10:00:00Z",
    ...overrides,
  };
}

// The body of the first such request; fails the test when there was none.
export function bodyOf(calls: StubbedCall[], method: string, path: string): unknown {
  const [call] = callsTo(calls, method, path);
  if (call === undefined) throw new Error(`no ${method} ${path} was sent`);
  return call.body;
}

export function catalogTableFixture(
  overrides: Partial<CatalogTableApiResponse> = {},
): CatalogTableApiResponse {
  return {
    catalog: "iceberg",
    namespace: ["retail"],
    name: "orders",
    uuid: "uuid-orders",
    format_version: 2,
    location: "s3://warehouse/retail/orders",
    current_snapshot_id: "9007199254740993",
    last_updated_ms: Date.now() - 3 * 3_600_000,
    schema: {
      schema_id: 0,
      fields: [
        { id: 1, name: "id", type: "long", required: true, doc: null },
        { id: 2, name: "placed_at", type: "timestamptz", required: false, doc: "order time" },
        {
          id: 3,
          name: "address",
          type: "struct<city: required string, zip: string>",
          required: false,
          doc: null,
        },
      ],
    },
    partition_spec: {
      spec_id: 0,
      fields: [{ source_id: 2, field_id: 1000, name: "placed_at_day", transform: "day" }],
    },
    sort_order: {
      order_id: 1,
      fields: [{ source_id: 1, transform: "identity", direction: "asc", null_order: "nulls-first" }],
    },
    snapshots: [
      {
        id: "9007199254740992",
        parent_id: null,
        timestamp_ms: Date.now() - 5 * 3_600_000,
        schema_id: 0,
        operation: "append",
        summary: { "added-records": "10" },
      },
      {
        id: "9007199254740993",
        parent_id: "9007199254740992",
        timestamp_ms: Date.now() - 3 * 3_600_000,
        schema_id: 0,
        operation: "overwrite",
        summary: { "added-records": "2" },
      },
    ],
    properties: { "write.format.default": "parquet", owner: "kc" },
    summary: { total_records: 1204331, total_data_files: 100, total_files_size: 335544320 },
    ...overrides,
  };
}

export function catalogTablePropertyFixture(
  overrides: Partial<CatalogTablePropertyApiResponse> & { key: string },
): CatalogTablePropertyApiResponse {
  return {
    current_value: null,
    default_value: null,
    default_source: "iceberg",
    modified: false,
    custom: false,
    resettable: true,
    description: `What ${overrides.key} does.`,
    ...overrides,
  };
}

// The properties of catalogTableFixture next to their defaults: one at its default, one changed,
// one Iceberg writes back on reset, one not resettable, one the catalog forces and a custom one.
// created-at is written by Polaris and never modified.
export function catalogTablePropertiesFixture(
  overrides: Partial<CatalogTablePropertiesApiResponse> = {},
): CatalogTablePropertiesApiResponse {
  return {
    uuid: "uuid-orders",
    iceberg_version: "1.10.1",
    properties: [
      catalogTablePropertyFixture({
        key: "commit.retry.num-retries",
        default_value: "4",
      }),
      catalogTablePropertyFixture({
        key: "created-at",
        current_value: "2026-11-14T00:00:00Z",
        default_source: null,
        resettable: false,
        description: "When Polaris created the table; written by Polaris.",
      }),
      catalogTablePropertyFixture({
        key: "format-version",
        current_value: "2",
        default_value: "2",
        resettable: false,
      }),
      catalogTablePropertyFixture({
        key: "gc.enabled",
        current_value: "false",
        default_value: "true",
        modified: true,
        resettable: false,
      }),
      catalogTablePropertyFixture({
        key: "owner",
        current_value: "kc",
        default_source: null,
        modified: true,
        custom: true,
        description: null,
      }),
      catalogTablePropertyFixture({
        key: "write.format.default",
        current_value: "orc",
        default_value: "parquet",
        modified: true,
      }),
      catalogTablePropertyFixture({
        key: "write.target-file-size-bytes",
        current_value: "134217728",
        default_value: "268435456",
        default_source: "catalog_override",
        modified: true,
        resettable: false,
      }),
    ],
    ...overrides,
  };
}
