import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { TableDiscoveryRuleApiResponse } from "../api/types";
import { jsonResponse } from "../test/fixtures";
import { DiscoveryRulesPage } from "./DiscoveryRulesPage";

function rule(overrides: Partial<TableDiscoveryRuleApiResponse>): TableDiscoveryRuleApiResponse {
  return {
    id: "rule",
    priority: 10,
    effect: "include",
    catalog_pattern: "iceberg",
    namespace_pattern: "e2e",
    table_pattern: "tm_e2e_*",
    preset_id: "preset-default",
    enabled: true,
    created_at: "2026-11-04T13:07:46Z",
    updated_at: "2026-11-04T13:07:46Z",
    ...overrides,
  };
}

const RULES = [
  rule({ id: "r-late", priority: 50, effect: "exclude", namespace_pattern: "*", table_pattern: "tmp_*", preset_id: null, enabled: false }),
  rule({ id: "r-early", priority: 10 }),
];

function stubApi(responses: Record<string, () => Response>) {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      const path = url.replace("/console/api", "");
      const make = responses[path];
      return Promise.resolve(make ? make() : jsonResponse({ detail: "not found" }, 404));
    }),
  );
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <DiscoveryRulesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const OK = {
  "/v1/table-discovery-rules": () => jsonResponse(RULES),
  "/v1/table-discovery-settings": () => jsonResponse({ enabled: true, updated_at: "2026-11-04T15:42:39Z" }),
  "/v1/table-maintenance-presets": () =>
    jsonResponse([{ id: "preset-default", name: "default", settings: {}, created_at: "x", updated_at: "x" }]),
};

afterEach(() => vi.unstubAllGlobals());

describe("DiscoveryRulesPage", () => {
  it("lists rules by priority, lowest first", async () => {
    stubApi(OK);
    renderPage();
    await screen.findByText("iceberg.e2e.tm_e2e_*");
    const priorities = screen
      .getAllByRole("row")
      .slice(1)
      .map((row) => within(row).getAllByRole("cell")[0]?.textContent);
    expect(priorities).toEqual(["10", "50"]);
  });

  it("shows the pattern, effect, preset name and state of each rule", async () => {
    stubApi(OK);
    renderPage();
    const include = (await screen.findByText("iceberg.e2e.tm_e2e_*")).closest("tr")!;
    expect(within(include as HTMLElement).getByText("Include")).toBeInTheDocument();
    expect(within(include as HTMLElement).getByRole("link", { name: "default" })).toHaveAttribute(
      "href",
      "/presets#preset-preset-default",
    );
    expect(within(include as HTMLElement).getByText("Enabled")).toBeInTheDocument();
    const exclude = screen.getByText("iceberg.*.tmp_*").closest("tr")!;
    expect(within(exclude as HTMLElement).getByText("Exclude")).toBeInTheDocument();
    expect(within(exclude as HTMLElement).getByText("—")).toBeInTheDocument();
    expect(within(exclude as HTMLElement).getByText("Disabled")).toBeInTheDocument();
  });

  it("shows whether discovery is on", async () => {
    stubApi(OK);
    renderPage();
    expect(await screen.findByText("Discovery is on")).toBeInTheDocument();
  });

  it("falls back to the preset id when the preset is unknown", async () => {
    stubApi({ ...OK, "/v1/table-maintenance-presets": () => jsonResponse([]) });
    renderPage();
    expect(await screen.findByRole("link", { name: "preset-default" })).toBeInTheDocument();
  });

  it("shows an error when the rules cannot be loaded", async () => {
    stubApi({ ...OK, "/v1/table-discovery-rules": () => jsonResponse({ detail: "boom" }, 500) });
    renderPage();
    expect(await screen.findByText(/Could not load discovery rules: boom/)).toBeInTheDocument();
  });
});
