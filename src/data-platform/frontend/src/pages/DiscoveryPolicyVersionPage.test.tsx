import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";
import type { DiscoveryRuleApiResponse, TableDiscoveryPolicyVersionApiResponse } from "../api/generated/model";
import { callsTo, stubCatalogApi, type StubHandler } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { DiscoveryPolicyVersionPage } from "./DiscoveryPolicyVersionPage";

const ORDERS: DiscoveryRuleApiResponse = {
  id: "dr-orders",
  outcome: "manage",
  conditions: [{ attribute: "namespace", operator: "glob", values: ["sales"] }],
};
const TEMPORARY: DiscoveryRuleApiResponse = {
  id: "dr-temporary",
  outcome: "unmanage",
  conditions: [{ attribute: "table_name", operator: "glob", values: ["tmp_*"] }],
};
const ARCHIVE: DiscoveryRuleApiResponse = {
  id: "dr-archive",
  outcome: "unmanage",
  conditions: [{ attribute: "table_name", operator: "glob", values: ["archive_*"] }],
};

function version(
  number: number,
  overrides: Partial<TableDiscoveryPolicyVersionApiResponse> = {},
): TableDiscoveryPolicyVersionApiResponse {
  return {
    id: "dp-01m7s6c3tqee0rhg00xry2zqqv",
    name: "sales-tables",
    is_default: false,
    version: number,
    description: "Sales tables",
    no_match_outcome: "unmanage",
    rules: [ORDERS, TEMPORARY],
    created_at: "2026-11-05T09:00:00Z",
    ...overrides,
  };
}

const VERSIONS = "/v1/discovery-policies/sales-tables/versions";

function stubApi(responses: Record<string, StubHandler> = {}) {
  return stubCatalogApi({
    [`GET ${VERSIONS}/1`]: () => jsonResponse(version(1, { rules: [ORDERS, ARCHIVE], no_match_outcome: "manage" })),
    [`GET ${VERSIONS}/2`]: () => jsonResponse(version(2)),
    ...responses,
  });
}

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/discovery-policies/:name/versions/:version" element={<DiscoveryPolicyVersionPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function changes(): HTMLElement {
  return screen.getByRole("list", { name: "Changes from v1" });
}

describe("DiscoveryPolicyVersionPage", () => {
  it("shows one kept version read only", async () => {
    stubApi();
    renderAt("/discovery-policies/sales-tables/versions/2");
    expect(await screen.findByRole("heading", { level: 1, name: "sales-tables v2" })).toBeInTheDocument();
    const facts = screen.getByRole("region", { name: "Policy" });
    expect(within(facts).getByText("Sales tables")).toBeInTheDocument();
    expect(within(facts).getByText("Do not manage")).toBeInTheDocument();
    const rules = screen.getByRole("table", { name: "Discovery rules, read top to bottom" });
    expect(within(rules).getByText("tmp_*")).toBeInTheDocument();
    expect(within(rules).queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save" })).not.toBeInTheDocument();
  });

  it("links back through Discovery policies and the policy", async () => {
    stubApi();
    renderAt("/discovery-policies/sales-tables/versions/2");
    await screen.findByRole("heading", { level: 1, name: "sales-tables v2" });
    const crumbs = within(screen.getByRole("navigation", { name: "Breadcrumb" }));
    expect(crumbs.getByRole("link", { name: "Discovery policies" })).toHaveAttribute("href", "/discovery-policies");
    expect(crumbs.getByRole("link", { name: "sales-tables" })).toHaveAttribute("href", "/discovery-policies/sales-tables");
    expect(crumbs.getByText("sales-tables v2")).toBeInTheDocument();
  });

  it("lists what the version changed from the one before it", async () => {
    stubApi();
    renderAt("/discovery-policies/sales-tables/versions/2");
    expect(await screen.findByRole("heading", { level: 2, name: "Changes from v1" })).toBeInTheDocument();
    const list = await screen.findByRole("list", { name: "Changes from v1" });
    const rows = within(list).getAllByRole("listitem").map((row) => row.textContent);
    expect(rows).toEqual([
      expect.stringContaining("When no rule matches"),
      expect.stringContaining("Do not manage: table name tmp_*"),
      expect.stringContaining("Do not manage: table name archive_*"),
    ]);
    expect(within(changes()).getByText("Added")).toBeInTheDocument();
    expect(within(changes()).getByText("Removed")).toBeInTheDocument();
  });

  it("says the first version is the first", async () => {
    const calls = stubApi();
    renderAt("/discovery-policies/sales-tables/versions/1");
    await screen.findByRole("heading", { level: 1, name: "sales-tables v1" });
    expect(screen.getByText("First version")).toBeInTheDocument();
    expect(callsTo(calls, "GET", `${VERSIONS}/0`)).toHaveLength(0);
  });

  it("says when the version before cannot be loaded", async () => {
    stubApi({ [`GET ${VERSIONS}/1`]: () => jsonResponse({ detail: "boom" }, 500) });
    renderAt("/discovery-policies/sales-tables/versions/2");
    expect(await screen.findByText("Could not load v1 to compare with: boom")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Discovery rules, read top to bottom" })).toBeInTheDocument();
  });

  it("refuses a version that is not a whole number without asking the API", async () => {
    const calls = stubApi();
    renderAt("/discovery-policies/sales-tables/versions/latest");
    expect(
      await screen.findByText("Could not load sales-tables vlatest: a version is a whole number."),
    ).toBeInTheDocument();
    expect(calls).toHaveLength(0);
  });

  it("shows the API's detail for a version that does not exist", async () => {
    stubApi({
      [`GET ${VERSIONS}/9`]: () => jsonResponse({ detail: "version 9 of discovery policy sales-tables not found" }, 404),
    });
    renderAt("/discovery-policies/sales-tables/versions/9");
    expect(
      await screen.findByText("Could not load sales-tables v9: version 9 of discovery policy sales-tables not found"),
    ).toBeInTheDocument();
  });
});
