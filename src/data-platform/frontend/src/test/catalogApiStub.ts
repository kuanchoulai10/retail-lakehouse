import { vi } from "vitest";
import type { CatalogApiResponse } from "../api/catalogTypes";
import { jsonResponse } from "./fixtures";

export type StubHandler = (body: unknown) => Response;

export interface StubbedCall {
  method: string;
  path: string;
  body: unknown;
}

// Stubs fetch with handlers keyed "METHOD /v1/path?query" (the /console/api prefix is dropped).
// An unstubbed request answers 500, so a test sees it instead of hanging.
export function stubCatalogApi(routes: Record<string, StubHandler>): StubbedCall[] {
  const calls: StubbedCall[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      const path = url.replace(/^\/console\/api/, "");
      const body = typeof init?.body === "string" ? (JSON.parse(init.body) as unknown) : undefined;
      calls.push({ method, path, body });
      const handler = routes[`${method} ${path}`];
      if (handler === undefined) {
        return Promise.resolve(jsonResponse({ detail: `no stub for ${method} ${path}` }, 500));
      }
      return Promise.resolve(handler(body));
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
