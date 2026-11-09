import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { stubCatalogApi, type StubHandler } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { MaintenancePanels } from "./MaintenancePanels";

const HEALTH = {
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
  ],
  position_delete_files: 0,
  equality_delete_files: 0,
};

const STORAGE = {
  current_bytes: 1024,
  current_files: 1,
  old_snapshot_bytes: 2048,
  old_snapshot_files: 2,
  window_days: 30,
  reclaimed: {
    rewritten_data_files: 0,
    added_data_files: 0,
    rewritten_bytes: 0,
    rewritten_manifests: 0,
    added_manifests: 0,
    expired_snapshots: 0,
    deleted_data_files: 0,
    deleted_manifest_files: 0,
    deleted_position_delete_files: 0,
    deleted_equality_delete_files: 0,
  },
  attempts_without_metrics: 0,
};

const TABLE = "/v1/tables/uuid-orders";

// Routes in `extra` come first, so they win over the defaults.
function stubApi(storage: StubHandler, extra: Record<string, StubHandler> = {}) {
  return stubCatalogApi({
    ...extra,
    [`GET ${TABLE}/health`]: () => jsonResponse(HEALTH),
    [`GET ${TABLE}/storage`]: storage,
    [`GET ${TABLE}/commits*`]: () => jsonResponse({ items: [], truncated: false }),
    [`GET ${TABLE}/table-maintenance-runs`]: () => jsonResponse([]),
  });
}

function renderTab(lastCommittedAt: string | null = new Date(Date.now() - 3 * 3_600_000).toISOString()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MaintenancePanels tableUuid="uuid-orders" lastCommittedAt={lastCommittedAt} />
    </QueryClientProvider>,
  );
}

describe("MaintenancePanels", () => {
  beforeEach(() => {
    stubApi(() => jsonResponse(STORAGE));
  });

  it("renders while storage is still loading", async () => {
    stubApi(() => new Promise<Response>(() => {}));
    renderTab();
    expect(await screen.findByText(/12 reducible files in 3 partitions/)).toBeInTheDocument();
    expect(screen.getByText("Loading storage…")).toBeInTheDocument();
  });

  it("shows storage once it arrives", async () => {
    renderTab();
    expect(await screen.findByText("2.0 KB")).toBeInTheDocument();
  });

  it("shows a storage error without hiding health", async () => {
    stubApi(() => jsonResponse({ detail: "scan failed" }, 500));
    renderTab();
    expect(await screen.findByText(/Could not load storage: scan failed/)).toBeInTheDocument();
    expect(await screen.findByText(/12 reducible files/)).toBeInTheDocument();
  });

  it("renders an empty table", async () => {
    renderTab(null);
    expect(await screen.findByText("No commits yet.")).toBeInTheDocument();
    expect(await screen.findByText("No maintenance runs yet.")).toBeInTheDocument();
  });

  it("asks for the last 24 hours of commits", async () => {
    const calls = stubApi(() => jsonResponse(STORAGE));
    renderTab();
    await screen.findByText(/12 reducible files/);
    const urls = calls.map((call) => call.path);
    expect(urls.some((u) => u.includes("/commits?since=") && u.endsWith("&limit=1000"))).toBe(true);
  });

  it("prefixes freshness counts with ≥ when the window was truncated", async () => {
    stubApi(() => jsonResponse(STORAGE), {
      [`GET ${TABLE}/commits?since=*`]: () =>
        jsonResponse({
          items: [
            {
              snapshot_id: "1",
              parent_id: null,
              committed_at: new Date().toISOString(),
              operation: "append",
              writer: "kafka_connect",
              added_records: null,
              deleted_records: null,
              added_data_files: null,
              deleted_data_files: null,
              added_delete_files: null,
              removed_delete_files: null,
              summary: {},
            },
          ],
          truncated: true,
        }),
    });
    renderTab();
    expect(await screen.findByText("≥ 1 commits in the last 24 h")).toBeInTheDocument();
  });
});
