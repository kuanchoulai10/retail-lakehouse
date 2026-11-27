import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import type {
  ListedTableDiscoveryPolicyApiResponse,
  ScannedCatalogApiResponse,
} from "../api/generated/model";
import { callsTo, stubCatalogApi, type StubHandler } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { DiscoveryPoliciesPage } from "./DiscoveryPoliciesPage";

function discoveryPolicy(
  overrides: Partial<ListedTableDiscoveryPolicyApiResponse>,
): ListedTableDiscoveryPolicyApiResponse {
  return {
    id: "dp-01m7s6c3tqee0rhg00xry2zqqx",
    name: "core-tables",
    version: 1,
    description: "",
    rules: [{ action: "include", table_name_pattern: "*" }],
    attachment_count: 0,
    created_at: "2026-11-01T09:00:00Z",
    updated_at: "2026-11-01T09:00:00Z",
    ...overrides,
  };
}

const SALES_RULES: ListedTableDiscoveryPolicyApiResponse["rules"] = [
  { action: "include", table_name_pattern: "orders*" },
  { action: "exclude", table_name_pattern: "tmp_*" },
];

// Listed out of order, as the page must not rely on the API's order.
const POLICIES = [
  discoveryPolicy({
    id: "dp-01m7s6c3tqee0rhg00xry2zqqv",
    name: "sales-tables",
    description: "Sales tables",
    version: 2,
    rules: SALES_RULES,
    attachment_count: 1,
  }),
  discoveryPolicy({ id: "dp-01m7s6c3tqee0rhg00xry2zqqw", name: "archive" }),
  discoveryPolicy({ name: "core-tables", description: "Every table" }),
];

function stubApi(responses: Record<string, StubHandler> = {}, catalogs: ScannedCatalogApiResponse[] = []) {
  return stubCatalogApi({
    "GET /v1/discovery-policies": () => jsonResponse({ policies: POLICIES }),
    "GET /v1/scanned-catalogs": () => jsonResponse({ catalogs }),
    ...responses,
  });
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <DiscoveryPoliciesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function policyRow(policyName: string): HTMLElement {
  const row = screen
    .getAllByRole("row")
    .find((r) => within(r).queryAllByRole("cell")[0]?.textContent?.startsWith(policyName));
  if (row === undefined) throw new Error(`no policy ${policyName}`);
  return row;
}

function cellUnder(row: HTMLElement, header: string): HTMLElement {
  const headers = screen.getAllByRole("columnheader").map((h) => h.textContent);
  const cell = within(row).getAllByRole("cell")[headers.indexOf(header)];
  if (cell === undefined) throw new Error(`no column ${header}`);
  return cell;
}

describe("DiscoveryPoliciesPage", { timeout: 15_000 }, () => {
  it("lists the policies by name, with no default among them", async () => {
    stubApi();
    renderPage();
    await screen.findByText("Sales tables");
    const names = screen
      .getAllByRole("row")
      .slice(1)
      .map((row) => within(row).getAllByRole("cell")[0]?.textContent);
    expect(names).toEqual(["archive", "core-tables", "sales-tables"]);
    expect(screen.queryByText("Default")).not.toBeInTheDocument();
  });

  it("links each name to the policy's page", async () => {
    stubApi();
    renderPage();
    await screen.findByText("Sales tables");
    expect(within(policyRow("sales-tables")).getByRole("link", { name: "sales-tables" })).toHaveAttribute(
      "href",
      "/discovery-policies/sales-tables",
    );
  });

  it("shows each policy's description, rule count, version and attachment count", async () => {
    stubApi();
    renderPage();
    await screen.findByText("Sales tables");
    expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
      "Name",
      "Description",
      "Rules",
      "Version",
      "Attached to",
      "Actions",
    ]);
    const sales = policyRow("sales-tables");
    expect(cellUnder(sales, "Rules")).toHaveTextContent("2");
    expect(cellUnder(sales, "Rules").querySelector(".tabular-nums")).not.toBeNull();
    expect(cellUnder(sales, "Version")).toHaveTextContent("2");
    expect(cellUnder(sales, "Attached to")).toHaveTextContent("1");
    expect(cellUnder(sales, "Attached to").querySelector(".tabular-nums")).not.toBeNull();
    const archive = policyRow("archive");
    expect(cellUnder(archive, "Description")).toHaveTextContent("—");
    expect(cellUnder(archive, "Rules")).toHaveTextContent("1");
  });

  it("lets an unattached policy be deleted", async () => {
    stubApi();
    renderPage();
    await screen.findByText("Sales tables");
    expect(within(policyRow("core-tables")).getByRole("button", { name: "Delete core-tables" })).toBeEnabled();
  });

  it("disables delete of an attached policy with its reason", async () => {
    stubApi();
    renderPage();
    await screen.findByText("Sales tables");
    const remove = within(policyRow("sales-tables")).getByRole("button", { name: "Delete sales-tables" });
    expect(remove).toBeDisabled();
    expect(remove).toHaveAccessibleDescription("Detach it from every target before deleting it.");
  });

  it("deletes an unattached policy once its name is typed, then refetches the list", async () => {
    const calls = stubApi({
      "DELETE /v1/discovery-policies/archive": () => new Response(null, { status: 204 }),
    });
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Sales tables");
    await user.click(within(policyRow("archive")).getByRole("button", { name: "Delete archive" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Delete discovery policy" });
    expect(within(dialog).getByText(/and every version of it/)).toBeInTheDocument();
    await user.type(within(dialog).getByRole("textbox", { name: "Type archive to confirm" }), "archive");
    await user.click(within(dialog).getByRole("button", { name: "Delete" }));

    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
    expect(callsTo(calls, "DELETE", "/v1/discovery-policies/archive")).toHaveLength(1);
    await waitFor(() => expect(callsTo(calls, "GET", "/v1/discovery-policies")).toHaveLength(2));
  });

  it("opens the create dialog from New policy", async () => {
    stubApi();
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: "New policy" }));
    expect(await screen.findByRole("dialog", { name: "New discovery policy" })).toBeInTheDocument();
  });

  it("says above the list which catalog discovery cannot read, and which no longer exists", async () => {
    stubApi({}, [
      {
        catalog: "finance",
        last_discovered_at: "2026-11-20T09:00:00Z",
        failure: {
          reason: "cannot_access",
          detail: "the platform's catalog credential cannot read catalog finance",
          failed_at: "2026-11-21T09:00:00Z",
        },
      },
      { catalog: "iceberg", last_discovered_at: "2026-11-21T09:00:00Z", failure: null },
      {
        catalog: "legacy",
        last_discovered_at: null,
        failure: { reason: "not_found", detail: "catalog legacy not found", failed_at: "2026-11-21T09:00:00Z" },
      },
    ]);
    renderPage();
    await screen.findByText("Sales tables");
    const alerts = await screen.findAllByRole("alert");
    expect(alerts.map((alert) => within(alert).getByText(/:$/).textContent)).toEqual([
      "Cannot access: finance",
      "Catalog not found: legacy",
    ]);
    expect(within(alerts[0]!).getByText("the platform's catalog credential cannot read catalog finance")).toBeInTheDocument();
    expect(within(alerts[1]!).getByText("catalog legacy not found")).toBeInTheDocument();
    expect(within(alerts[0]!).getByText("finance", { selector: ".font-mono" })).toBeInTheDocument();
    const list = screen.getByRole("table");
    expect(alerts[1]!.compareDocumentPosition(list) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("shows no banner while every scanned catalog reads", async () => {
    stubApi({}, [{ catalog: "iceberg", last_discovered_at: "2026-11-21T09:00:00Z", failure: null }]);
    renderPage();
    await screen.findByText("Sales tables");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("says so when the scanned catalogs cannot be read, and still lists the policies", async () => {
    stubApi({ "GET /v1/scanned-catalogs": () => jsonResponse({ detail: "database unavailable" }, 500) });
    renderPage();
    expect(
      await screen.findByText("Could not check which catalogs discovery can read: database unavailable"),
    ).toBeInTheDocument();
    expect(screen.getByText("Sales tables")).toBeInTheDocument();
  });

  it("shows an error when the policies cannot be loaded", async () => {
    stubApi({ "GET /v1/discovery-policies": () => jsonResponse({ detail: "boom" }, 500) });
    renderPage();
    expect(await screen.findByText("Could not load discovery policies: boom")).toBeInTheDocument();
  });
});
