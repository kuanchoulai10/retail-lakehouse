import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getGetTableHealthQueryKey } from "../../api/generated/tables/tables";
import type { TableApiResponse } from "../../api/generated/model";
import { stubCatalogApi, type StubbedCall } from "../../test/catalogApiStub";
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
  return stubCatalogApi({
    "GET /v1/tables/uuid-orders": () => jsonResponse(table),
    "GET /v1/table-maintenance-presets/default": () =>
      jsonResponse({ id: "default", name: "Default", settings: PRESET_SETTINGS }),
    "PUT /v1/tables/uuid-orders/settings": () => putResponse(),
  });
}

function renderTab() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  client.setQueryData(getGetTableHealthQueryKey("uuid-orders"), {});
  render(
    <QueryClientProvider client={client}>
      <SettingsTab tableUuid="uuid-orders" />
    </QueryClientProvider>,
  );
  return client;
}

function healthIsStale(client: QueryClient) {
  return client.getQueryState(getGetTableHealthQueryKey("uuid-orders"))?.isInvalidated;
}

function puts(calls: StubbedCall[]) {
  return calls.filter((call) => call.method === "PUT");
}

describe("SettingsTab", () => {
  let table: TableApiResponse;
  beforeEach(() => {
    table = tableFixture({ settings: SETTINGS });
  });

  it("saves the whole settings object with the changed field", async () => {
    const calls = mockApi(table, () => jsonResponse(table));
    renderTab();
    const group = await screen.findByRole("group", { name: "rewrite_data_files" });
    const field = within(group).getByLabelText("min_reducible_files");
    await userEvent.clear(field);
    await userEvent.type(field, "25");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await vi.waitFor(() => expect(puts(calls)[0]).toBeDefined());
    const [put] = puts(calls);
    expect(put?.path).toBe("/v1/tables/uuid-orders/settings");
    expect(put?.body).toEqual({
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

  it("resets to the preset settings after confirming in the dialog", async () => {
    const calls = mockApi(table, () => jsonResponse(table));
    renderTab();
    await userEvent.click(await screen.findByRole("button", { name: "Reset to preset" }));
    expect(await screen.findByRole("alertdialog")).toBeInTheDocument();
    expect(puts(calls)).toHaveLength(0);
    await userEvent.click(screen.getByRole("button", { name: "Confirm reset" }));
    await vi.waitFor(() => expect(puts(calls)).toHaveLength(1));
    expect(puts(calls)[0]?.body).toEqual(PRESET_SETTINGS);
  });

  it("marks health stale after a save", async () => {
    mockApi(table, () => jsonResponse(table));
    const client = renderTab();
    await screen.findByRole("group", { name: "rewrite_data_files" });
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await vi.waitFor(() => {
      expect(healthIsStale(client)).toBe(true);
    });
  });

  it("marks health stale after a reset", async () => {
    mockApi(table, () => jsonResponse(table));
    const client = renderTab();
    await userEvent.click(await screen.findByRole("button", { name: "Reset to preset" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirm reset" }));
    await vi.waitFor(() => {
      expect(healthIsStale(client)).toBe(true);
    });
  });

  it("hides Reset to preset when the table has no source preset", async () => {
    mockApi({ ...table, source_preset_id: null }, () => jsonResponse(table));
    renderTab();
    await screen.findByRole("group", { name: "rewrite_data_files" });
    expect(screen.queryByRole("button", { name: "Reset to preset" })).not.toBeInTheDocument();
  });

  it("closes the reset dialog on Escape without saving and returns focus", async () => {
    const calls = mockApi(table, () => jsonResponse(table));
    renderTab();
    const trigger = await screen.findByRole("button", { name: "Reset to preset" });
    await userEvent.click(trigger);
    expect(await screen.findByRole("alertdialog")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    await vi.waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
    expect(puts(calls)).toHaveLength(0);
    expect(trigger).toHaveFocus();
  });

  it("renders each operation in a panel titled with its procedure name", async () => {
    mockApi(table, () => jsonResponse(table));
    renderTab();
    for (const name of [
      "rewrite_data_files",
      "rewrite_manifests",
      "expire_snapshots",
      "remove_orphan_files",
    ]) {
      const heading = await screen.findByRole("heading", { name });
      expect(within(heading.closest("section") as HTMLElement).getByRole("group", { name })).toBeInTheDocument();
    }
  });

  it("toggles an operation with a switch", async () => {
    const calls = mockApi(table, () => jsonResponse(table));
    renderTab();
    const group = await screen.findByRole("group", { name: "remove_orphan_files" });
    const toggle = within(group).getByRole("switch", { name: "enabled" });
    expect(toggle).not.toBeChecked();
    await userEvent.click(toggle);
    expect(toggle).toBeChecked();
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await vi.waitFor(() => expect(puts(calls)[0]).toBeDefined());
    const body = puts(calls)[0]?.body as { remove_orphan_files: { enabled: boolean } };
    expect(body.remove_orphan_files.enabled).toBe(true);
  });
});
