import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { TableMaintenancePresetApiResponse } from "../api/types";
import { jsonResponse } from "../test/fixtures";
import { PresetsPage } from "./PresetsPage";

const PRESET: TableMaintenancePresetApiResponse = {
  id: "preset-default",
  name: "default",
  settings: {
    reconcile_interval_seconds: 3600,
    rewrite_data_files: { enabled: true, min_interval_seconds: 3600, target_file_size_bytes: null },
    remove_orphan_files: { enabled: false, older_than_seconds: 259200 },
  },
  created_at: "2026-11-04T13:06:08Z",
  updated_at: "2026-11-04T13:06:08Z",
};

function renderPage(response: Response) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <PresetsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("PresetsPage", () => {
  it("reads the presets endpoint", async () => {
    renderPage(jsonResponse([PRESET]));
    await screen.findByRole("region", { name: "default" });
    expect(fetch).toHaveBeenCalledWith("/console/api/v1/table-maintenance-presets", expect.anything());
  });

  it("shows one panel per preset with its id and reconcile interval", async () => {
    renderPage(jsonResponse([PRESET]));
    const panel = await screen.findByRole("region", { name: "default" });
    expect(within(panel).getByText("preset-default")).toBeInTheDocument();
    expect(within(panel).getByText("Reconcile interval").nextElementSibling).toHaveTextContent("1 h");
  });

  it("lists each operation with its state and parameters", async () => {
    renderPage(jsonResponse([PRESET]));
    const panel = await screen.findByRole("region", { name: "default" });
    const rewrite = within(panel).getByRole("row", { name: /rewrite_data_files/ });
    expect(within(rewrite).getByText("Enabled")).toBeInTheDocument();
    expect(within(rewrite).getByText("min_interval_seconds")).toBeInTheDocument();
    expect(within(rewrite).getByText("Default")).toBeInTheDocument();
    const orphans = within(panel).getByRole("row", { name: /remove_orphan_files/ });
    expect(within(orphans).getByText("Disabled")).toBeInTheDocument();
    expect(within(orphans).getByText("3 d")).toBeInTheDocument();
  });

  it("says so when there are no presets", async () => {
    renderPage(jsonResponse([]));
    expect(await screen.findByText("No presets.")).toBeInTheDocument();
  });

  it("shows an error when the presets cannot be loaded", async () => {
    renderPage(jsonResponse({ detail: "boom" }, 500));
    expect(await screen.findByText(/Could not load presets: boom/)).toBeInTheDocument();
  });
});
