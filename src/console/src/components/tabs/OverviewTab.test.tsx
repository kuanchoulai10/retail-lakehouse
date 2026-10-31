import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { jsonResponse, metadataFixture } from "../../test/fixtures";
import { OverviewTab } from "./OverviewTab";

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
  reclaimed: {},
  attempts_without_metrics: 0,
};

function stubFetch(storage: () => Promise<Response>, commits: unknown[] = []) {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (url.endsWith("/health")) return Promise.resolve(jsonResponse(HEALTH));
      if (url.endsWith("/storage")) return storage();
      if (url.includes("/commits")) {
        return Promise.resolve(jsonResponse({ items: commits, truncated: false }));
      }
      return Promise.resolve(jsonResponse([]));
    }),
  );
}

function renderTab(metadata = metadataFixture()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <OverviewTab tableUuid="uuid-orders" metadata={metadata} />
    </QueryClientProvider>,
  );
}

describe("OverviewTab", () => {
  beforeEach(() => {
    stubFetch(() => Promise.resolve(jsonResponse(STORAGE)));
  });

  it("renders while storage is still loading", async () => {
    stubFetch(() => new Promise<Response>(() => {}));
    renderTab();
    expect(await screen.findByText(/12 reducible files in 3 partitions/)).toBeInTheDocument();
    expect(screen.getByText("Loading storage…")).toBeInTheDocument();
  });

  it("shows storage once it arrives", async () => {
    renderTab();
    expect(await screen.findByText("2.0 KB")).toBeInTheDocument();
  });

  it("shows a storage error without hiding health", async () => {
    stubFetch(() => Promise.resolve(jsonResponse({ detail: "scan failed" }, 500)));
    renderTab();
    expect(await screen.findByText(/Could not load storage: scan failed/)).toBeInTheDocument();
    expect(await screen.findByText(/12 reducible files/)).toBeInTheDocument();
  });

  it("renders an empty table", async () => {
    renderTab(
      metadataFixture({
        snapshot_count: 0,
        current_snapshot_id: null,
        last_committed_at: null,
      }),
    );
    expect(await screen.findByText("No commits yet.")).toBeInTheDocument();
    expect(await screen.findByText("No maintenance runs yet.")).toBeInTheDocument();
  });

  it("asks for the last 24 hours of commits", async () => {
    renderTab();
    await screen.findByText(/12 reducible files/);
    const urls = vi.mocked(fetch).mock.calls.map((call) => String(call[0]));
    expect(urls.some((u) => u.includes("/commits?since=") && u.endsWith("&limit=1000"))).toBe(true);
  });

  it("prefixes freshness counts with ≥ when the window was truncated", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.endsWith("/health")) return Promise.resolve(jsonResponse(HEALTH));
        if (url.endsWith("/storage")) return Promise.resolve(jsonResponse(STORAGE));
        if (url.includes("since=")) {
          return Promise.resolve(
            jsonResponse({
              items: [
                {
                  snapshot_id: 1,
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
          );
        }
        return Promise.resolve(jsonResponse(url.includes("/commits") ? { items: [], truncated: false } : []));
      }),
    );
    renderTab();
    expect(await screen.findByText("≥ 1 commits in the last 24 h")).toBeInTheDocument();
  });
});
