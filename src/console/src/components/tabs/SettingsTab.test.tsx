import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TableApiResponse } from "../../api/types";
import { jsonResponse, tableFixture } from "../../test/fixtures";
import { SettingsTab } from "./SettingsTab";

const SETTINGS = {
  reconcile_interval_seconds: 600,
  future_key: { keep: "me" },
  rewrite_data_files: {
    enabled: true,
    min_interval_seconds: 3600,
    scope: "table",
    target_file_size_bytes: null,
    min_reducible_files: 10,
  },
  rewrite_manifests: { enabled: true, min_interval_seconds: 3600, min_small_manifests: 5 },
  expire_snapshots: { enabled: true, min_interval_seconds: 3600, older_than_seconds: 86400, retain_last: 5 },
  remove_orphan_files: { enabled: false, min_interval_seconds: 86400, older_than_seconds: 259200 },
};
const PRESET_SETTINGS = { rewrite_data_files: { enabled: true, min_reducible_files: 2 } };

function mockApi(table: TableApiResponse, putResponse: () => Response) {
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (init?.method === "PUT") return Promise.resolve(putResponse());
    if (url.endsWith("/v1/table-maintenance-presets/default")) {
      return Promise.resolve(
        jsonResponse({ id: "default", name: "Default", settings: PRESET_SETTINGS }),
      );
    }
    return Promise.resolve(jsonResponse(table));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderTab() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  client.setQueryData(["health", "uuid-orders"], {});
  client.setQueryData(["metadata", "uuid-orders"], {});
  render(
    <QueryClientProvider client={client}>
      <SettingsTab tableUuid="uuid-orders" />
    </QueryClientProvider>,
  );
  return client;
}

function isStale(client: QueryClient, key: string) {
  return client.getQueryState([key, "uuid-orders"])?.isInvalidated;
}

function puts(fetchMock: ReturnType<typeof mockApi>) {
  return fetchMock.mock.calls.filter(([, init]) => init?.method === "PUT");
}

describe("SettingsTab", () => {
  let table: TableApiResponse;
  beforeEach(() => {
    table = tableFixture({ settings: SETTINGS });
  });

  it("saves the whole settings object with the changed field", async () => {
    const fetchMock = mockApi(table, () => jsonResponse(table));
    renderTab();
    const group = await screen.findByRole("group", { name: "rewrite_data_files" });
    const field = within(group).getByLabelText("min_reducible_files");
    await userEvent.clear(field);
    await userEvent.type(field, "25");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    const [url, init] = puts(fetchMock)[0] ?? [];
    expect(url).toBe("/console/api/v1/tables/uuid-orders/settings");
    expect(JSON.parse(String(init?.body))).toEqual({
      ...SETTINGS,
      rewrite_data_files: { ...SETTINGS.rewrite_data_files, min_reducible_files: 25 },
    });
  });

  it("shows the API detail when the save is rejected", async () => {
    mockApi(table, () => jsonResponse({ detail: "min_reducible_files must be positive" }, 422));
    renderTab();
    await screen.findByRole("group", { name: "rewrite_data_files" });
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "min_reducible_files must be positive",
    );
  });

  it("resets to the preset settings after an inline confirm", async () => {
    const fetchMock = mockApi(table, () => jsonResponse(table));
    renderTab();
    await userEvent.click(await screen.findByRole("button", { name: "Reset to preset" }));
    expect(puts(fetchMock)).toHaveLength(0);
    await userEvent.click(screen.getByRole("button", { name: "Confirm reset" }));
    await vi.waitFor(() => expect(puts(fetchMock)).toHaveLength(1));
    expect(JSON.parse(String(puts(fetchMock)[0]?.[1]?.body))).toEqual(PRESET_SETTINGS);
  });

  it("marks health and metadata stale after a save", async () => {
    mockApi(table, () => jsonResponse(table));
    const client = renderTab();
    await screen.findByRole("group", { name: "rewrite_data_files" });
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await vi.waitFor(() => {
      expect(isStale(client, "health")).toBe(true);
      expect(isStale(client, "metadata")).toBe(true);
    });
  });

  it("marks health and metadata stale after a reset", async () => {
    mockApi(table, () => jsonResponse(table));
    const client = renderTab();
    await userEvent.click(await screen.findByRole("button", { name: "Reset to preset" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirm reset" }));
    await vi.waitFor(() => {
      expect(isStale(client, "health")).toBe(true);
      expect(isStale(client, "metadata")).toBe(true);
    });
  });

  it("hides Reset to preset when the table has no source preset", async () => {
    mockApi({ ...table, source_preset_id: null }, () => jsonResponse(table));
    renderTab();
    await screen.findByRole("group", { name: "rewrite_data_files" });
    expect(screen.queryByRole("button", { name: "Reset to preset" })).not.toBeInTheDocument();
  });
});
