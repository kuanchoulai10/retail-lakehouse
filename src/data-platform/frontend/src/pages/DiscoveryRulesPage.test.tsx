import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import type { TableDiscoveryRuleApiResponse } from "../api/generated/model";
import { stubCatalogApi } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { DiscoveryRulesPage } from "./DiscoveryRulesPage";

function rule(overrides: Partial<TableDiscoveryRuleApiResponse>): TableDiscoveryRuleApiResponse {
  return {
    id: "rule",
    priority: 10,
    action: "include",
    catalogs: ["iceberg"],
    namespaces: ["e2e"],
    tables: ["tm_e2e_*"],
    enabled: true,
    created_at: "2026-11-04T13:07:46Z",
    updated_at: "2026-11-04T13:07:46Z",
    ...overrides,
  };
}

const RULES = [
  rule({ id: "r-late", priority: 50, action: "exclude", namespaces: ["*"], tables: ["tmp_*", "staging_*"], enabled: false }),
  rule({ id: "r-early", priority: 10 }),
];

// Answers the GETs in `responses` by path; any other GET is a 404.
function stubApi(responses: Record<string, () => Response>) {
  const routes = Object.fromEntries(Object.entries(responses).map(([path, make]) => [`GET ${path}`, make]));
  stubCatalogApi({ ...routes, "GET *": () => jsonResponse({ detail: "not found" }, 404) });
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
  "/v1/discovery-rules": () => jsonResponse({ version: 2, rules: RULES }),
};

describe("DiscoveryRulesPage", () => {
  it("lists rules by priority, lowest first", async () => {
    stubApi(OK);
    renderPage();
    await screen.findByText("tm_e2e_*");
    const priorities = screen
      .getAllByRole("row")
      .slice(1)
      .map((row) => within(row).getAllByRole("cell")[0]?.textContent);
    expect(priorities).toEqual(["10", "50"]);
  });

  it("shows the globs, action and state of each rule", async () => {
    stubApi(OK);
    renderPage();
    const include = (await screen.findByText("tm_e2e_*")).closest("tr")!;
    expect(within(include as HTMLElement).getByText("Include")).toBeInTheDocument();
    expect(within(include as HTMLElement).getByText("e2e")).toBeInTheDocument();
    expect(within(include as HTMLElement).getByText("Enabled")).toBeInTheDocument();
    const exclude = screen.getByText("tmp_*, staging_*").closest("tr")!;
    expect(within(exclude as HTMLElement).getByText("Exclude")).toBeInTheDocument();
    expect(within(exclude as HTMLElement).getByText("Disabled")).toBeInTheDocument();
  });

  it("has no discovery switch", async () => {
    stubApi(OK);
    renderPage();
    await screen.findByText("tm_e2e_*");
    expect(screen.queryByText(/Discovery is (on|off)/)).not.toBeInTheDocument();
    expect(screen.queryByRole("switch")).not.toBeInTheDocument();
  });

  it("shows an error when the rules cannot be loaded", async () => {
    stubApi({ ...OK, "/v1/discovery-rules": () => jsonResponse({ detail: "boom" }, 500) });
    renderPage();
    expect(await screen.findByText(/Could not load discovery rules: boom/)).toBeInTheDocument();
  });
});
