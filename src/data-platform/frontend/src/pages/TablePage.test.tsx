import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { describe, expect, it, vi } from "vitest";
import type { CatalogTableApiResponse, TableApiResponse } from "../api/generated/model";
import { getListCatalogTablesQueryKey } from "../api/generated/tables/tables";
import {
  bodyOf,
  callsTo,
  catalogTableFixture,
  catalogTablePropertiesFixture,
  stubCatalogApi,
  type StubHandler,
} from "../test/catalogApiStub";
import { jsonResponse, policyContentFixture, policyFixture, tableFixture } from "../test/fixtures";
import { settle, SuspendForever } from "../test/SuspendForever";
import { temporalWorkflowsUrl } from "../lib/temporalWorkflowsUrl";
import { TablePage } from "./TablePage";

const TABLE = "/v1/catalogs/iceberg/namespaces/retail/tables/orders";
const PAGE = "/catalogs/iceberg/namespaces/retail/tables/orders";
const TABS = ["Overview", "Schema", "Properties", "Commits", "Maintenance", "Candidates", "Reconciliations"];

function Location() {
  const location = useLocation();
  return <p data-testid="location">{location.pathname}</p>;
}

function renderAt(path: string, namespacePage: ReactNode = <p>namespace page</p>) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/catalogs/:catalog/namespaces/:namespace" element={namespacePage} />
          <Route path="/catalogs/:catalog/namespaces/:namespace/tables/:table/:tab?" element={<TablePage />} />
        </Routes>
        <Location />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return client;
}

function maintenance(overrides: Partial<TableApiResponse> = {}): TableApiResponse {
  return tableFixture({ namespace: "retail", ...overrides });
}

interface Options {
  table?: CatalogTableApiResponse;
  covered?: string[];
  maintenanceTable?: () => Response;
  extra?: Record<string, StubHandler>;
}

function stubTable({ table = catalogTableFixture(), covered = ["iceberg"], maintenanceTable, extra = {} }: Options = {}) {
  return stubCatalogApi({
    [`GET ${TABLE}`]: () => jsonResponse(table),
    [`GET ${TABLE}/properties`]: () => jsonResponse(catalogTablePropertiesFixture()),
    "GET /v1/discovery-rules/catalogs": () => jsonResponse({ catalogs: covered }),
    "GET /v1/discovery-rules": () => jsonResponse({ version: 1, rules: [RULE] }),
    "GET /v1/tables/uuid-orders": maintenanceTable ?? (() => jsonResponse(maintenance())),
    "GET /v1/tables/uuid-orders/commits*": () => jsonResponse({ items: [], truncated: false }),
    "GET /v1/tables/uuid-orders/health": () =>
      jsonResponse({
        scheduled: true,
        not_scheduled_reason: null,
        operations: [],
        position_delete_files: 0,
        equality_delete_files: 0,
      }),
    "GET /v1/tables/uuid-orders/storage": () => jsonResponse({ detail: "not in this test" }, 503),
    "GET /v1/tables/uuid-orders/table-maintenance-runs": () => jsonResponse([]),
    ...extra,
  });
}

const RULE = {
  id: "rule-1",
  priority: 10,
  action: "include",
  enabled: true,
  catalogs: ["iceberg"],
  namespaces: ["*"],
  tables: ["*"],
  created_at: "2026-10-30T10:00:00Z",
  updated_at: "2026-10-30T10:00:00Z",
};

const UNMANAGED: [string, Options, string][] = [
  ["catalog-not-covered", { covered: ["other"] }, "this catalog is not covered by maintenance"],
  [
    "not-found",
    { maintenanceTable: () => jsonResponse({ detail: "table uuid-orders not found" }, 404) },
    "discovery has not found this table yet",
  ],
  [
    "unmanaged",
    { maintenanceTable: () => jsonResponse(maintenance({ status: "unmanaged" })) },
    "the discovery rules do not include this table",
  ],
  [
    "dropped",
    { maintenanceTable: () => jsonResponse(maintenance({ status: "dropped" })) },
    "maintenance recorded this table as dropped",
  ],
];

async function openAction(user: ReturnType<typeof userEvent.setup>, label: string) {
  await user.click(await screen.findByRole("button", { name: "Actions" }));
  await user.click(await screen.findByRole("menuitem", { name: label }));
}

function tabNames(): string[] {
  return screen.getAllByRole("tab").map((tab) => tab.textContent ?? "");
}

// These tests type into dialogs, which takes seconds under a loaded parallel run.
describe("TablePage", { timeout: 15_000 }, () => {
  it("every table shows the same tabs, with no settings tab", async () => {
    stubTable();
    renderAt(PAGE);
    await screen.findByText("Maintenance: managed");
    expect(tabNames()).toEqual(TABS);
  });

  it("every table shows the same tabs when maintenance does not manage it", async () => {
    stubTable({ covered: [] });
    renderAt(PAGE);
    await screen.findByText("Maintenance: not managed");
    expect(tabNames()).toEqual(TABS);
  });

  it("the old settings path shows the overview", async () => {
    stubTable();
    renderAt(`${PAGE}/settings`);
    expect(await screen.findByText("Maintenance: managed")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
  });

  describe.each(UNMANAGED)("unmanaged table (%s)", (_reason, options, message) => {
    it.each(["commits", "maintenance", "candidates", "reconciliations"])(
      "unmanaged table shows the empty state on commits maintenance candidates and reconciliations: %s",
      async (tab) => {
        stubTable(options);
        renderAt(`${PAGE}/${tab}`);
        expect(await screen.findByText(message)).toBeInTheDocument();
        expect(screen.getByText("Maintenance does not manage this table")).toBeInTheDocument();
        expect(screen.queryByRole("button", { name: "Run maintenance" })).not.toBeInTheDocument();
        expect(screen.queryByRole("button", { name: /Pause|Resume/ })).not.toBeInTheDocument();
      },
    );
  });

  it("overview shows the policy that applies and its dry run below the Table panel, and the header shows neither", async () => {
    const applicable = { ...policyContentFixture(), name: "scratch", version: 2, dry_run: true, target: null };
    const calls = stubTable({ extra: { "GET /v1/tables/uuid-orders/applicable-policy": () => jsonResponse(applicable) } });
    renderAt(PAGE);
    const panel = within(await screen.findByRole("region", { name: "Maintenance policy" }));
    expect(await panel.findByText("Platform default")).toBeInTheDocument();
    expect(panel.getByRole("link", { name: "scratch v2" })).toBeInTheDocument();
    expect(panel.getByText("Dry run")).toBeInTheDocument();
    const table = screen.getByRole("region", { name: "Table" });
    expect(table.compareDocumentPosition(screen.getByRole("region", { name: "Maintenance policy" }))).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    );
    const heading = screen.getByRole("heading", { level: 1, name: "orders" });
    const header = within(heading.closest("header") as HTMLElement);
    expect(header.queryByText("Dry run")).not.toBeInTheDocument();
    expect(header.queryByText(/Policy:/)).not.toBeInTheDocument();
    expect(header.queryByText(/Rule:/)).not.toBeInTheDocument();
    expect(header.queryByText("Managed")).not.toBeInTheDocument();
    expect(callsTo(calls, "GET", "/v1/tables/uuid-orders/applicable-policy")).toHaveLength(1);
  });

  it("the old policy path lands on the overview url, with the policy block and no 404", async () => {
    stubTable();
    renderAt(`${PAGE}/policy`);
    expect(await screen.findByRole("region", { name: "Maintenance policy" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("location")).toHaveTextContent(`${PAGE}/overview`);
    expect(screen.queryByText(/not found/i)).not.toBeInTheDocument();
  });

  it("overview asks by name for a table maintenance has no record of, and attaches to it", async () => {
    const byName = "/v1/applicable-policy?catalog=iceberg&namespace=retail&table=orders";
    const calls = stubTable({
      covered: ["other"],
      maintenanceTable: () => jsonResponse({ detail: "table uuid-orders not found" }, 404),
      extra: {
        [`GET ${byName}`]: () => jsonResponse({ ...policyContentFixture(), name: "default", version: 1, target: null }),
        "GET /v1/maintenance-policies": () =>
          jsonResponse({ policies: [policyFixture({ name: "default" }), policyFixture({ name: "scratch" })] }),
        "PUT /v1/maintenance-policies/scratch/mappings": () =>
          jsonResponse({
            policy_name: "scratch",
            target: { type: "table", path: ["iceberg", "retail", "orders"], table_uuid: "uuid-orders" },
            attached_at: "2026-11-12T09:00:00Z",
          }),
      },
    });
    renderAt(PAGE);
    expect(await screen.findByText("Platform default")).toBeInTheDocument();
    expect(screen.getByText("this catalog is not covered by maintenance")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Attach policy" }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("combobox", { name: "Policy" }));
    await userEvent.click(await screen.findByRole("option", { name: "scratch" }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Attach" }));
    await waitFor(() => expect(callsTo(calls, "GET", byName)).toHaveLength(2));
    expect(bodyOf(calls, "PUT", "/v1/maintenance-policies/scratch/mappings")).toEqual({
      target: { type: "table", path: ["iceberg", "retail", "orders"] },
    });
    expect(callsTo(calls, "GET", "/v1/tables/uuid-orders/applicable-policy")).toHaveLength(0);
  });

  it("never asks maintenance about a catalog it does not cover for the commits tab", async () => {
    const calls = stubTable({ covered: [] });
    renderAt(`${PAGE}/commits`);
    await screen.findByText("this catalog is not covered by maintenance");
    expect(callsTo(calls, "GET", "/v1/tables/uuid-orders/commits")).toHaveLength(0);
  });

  it("managed marker on overview", async () => {
    stubTable();
    renderAt(PAGE);
    const summary = await screen.findByRole("region", { name: "Table" });
    expect(await within(summary).findByText("Maintenance: managed")).toBeInTheDocument();
    expect(within(summary).getByText("s3://warehouse/retail/orders")).toBeInTheDocument();
    expect(within(summary).getByText("9007199254740993")).toBeInTheDocument();
  });

  it("overview holds only the Table panel: no health, storage, freshness, commits or runs", async () => {
    const calls = stubTable();
    renderAt(PAGE);
    const summary = await screen.findByRole("region", { name: "Table" });
    await within(summary).findByText("Maintenance: managed");
    await settle();
    for (const name of ["Health", "Storage", "Freshness & activity", "Recent commits", "Last maintenance run"]) {
      expect(screen.queryByRole("region", { name })).not.toBeInTheDocument();
    }
    expect(screen.queryByText("No maintenance runs yet.")).not.toBeInTheDocument();
    for (const path of ["health", "storage", "commits*", "table-maintenance-runs"]) {
      expect(calls.filter((call) => call.path.startsWith(`/v1/tables/uuid-orders/${path.replace("*", "")}`))).toHaveLength(0);
    }
    expect(screen.queryByText("Maintenance does not manage this table")).not.toBeInTheDocument();
  });

  it("overview names the discovery rule that selected a managed table, by priority", async () => {
    stubTable();
    renderAt(PAGE);
    const summary = await screen.findByRole("region", { name: "Table" });
    const link = await within(summary).findByRole("link", { name: "Priority 10" });
    expect(link).toHaveAttribute("href", "/discovery-rules");
    expect(within(summary).getByText("Maintenance: managed")).toBeInTheDocument();
    expect(within(summary).queryByText("rule-1")).not.toBeInTheDocument();
  });

  it("overview shows no rule when the rule is not in the rule list", async () => {
    stubTable({ extra: { "GET /v1/discovery-rules": () => jsonResponse({ version: 1, rules: [] }) } });
    renderAt(PAGE);
    const summary = await screen.findByRole("region", { name: "Table" });
    await within(summary).findByText("Maintenance: managed");
    await settle();
    expect(within(summary).queryByRole("link", { name: /Priority/ })).not.toBeInTheDocument();
  });

  it("overview does not ask for the discovery rules when the table is not managed", async () => {
    const calls = stubTable({ maintenanceTable: () => jsonResponse(maintenance({ status: "unmanaged" })) });
    renderAt(PAGE);
    await screen.findByText("Maintenance: not managed");
    await settle();
    expect(callsTo(calls, "GET", "/v1/discovery-rules")).toHaveLength(0);
  });

  it("maintenance tab links to the table's running workflows in Temporal", async () => {
    stubTable();
    renderAt(`${PAGE}/maintenance`);
    const link = await screen.findByRole("link", { name: "Running workflows in Temporal" });
    expect(link).toHaveAttribute("href", temporalWorkflowsUrl("uuid-orders"));
  });

  it("shows the not managed marker and the empty state on overview", async () => {
    stubTable({ maintenanceTable: () => jsonResponse(maintenance({ status: "unmanaged" })) });
    renderAt(PAGE);
    const summary = await screen.findByRole("region", { name: "Table" });
    expect(await within(summary).findByText("Maintenance: not managed")).toBeInTheDocument();
    expect(screen.getByText("the discovery rules do not include this table")).toBeInTheDocument();
  });

  it("shows the header numbers from the catalog summary", async () => {
    stubTable();
    renderAt(PAGE);
    const heading = await screen.findByRole("heading", { level: 1, name: "orders" });
    const header = within(heading.closest("header") as HTMLElement);
    expect(header.getByText("1,204,331 rows")).toBeInTheDocument();
    expect(header.getByText("100 data files")).toBeInTheDocument();
    expect(header.getByText("320.0 MB")).toBeInTheDocument();
    expect(header.getByText("2 snapshots")).toBeInTheDocument();
    const crumbs = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(within(crumbs).getByRole("link", { name: "retail" })).toHaveAttribute(
      "href",
      "/catalogs/iceberg/namespaces/retail",
    );
  });

  it("shows run maintenance and no pause or resume when the table is managed", async () => {
    stubTable();
    renderAt(PAGE);
    expect(await screen.findByRole("button", { name: "Run maintenance" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: /Pause|Resume/ })).not.toBeInTheDocument();
  });

  it("shows the polaris tabs when maintenance fails to answer", async () => {
    stubTable({ maintenanceTable: () => jsonResponse({ detail: "database down" }, 500) });
    renderAt(`${PAGE}/properties`);
    expect(await screen.findByText("write.format.default")).toBeInTheDocument();
  });

  it("shows the maintenance error on a maintenance tab", async () => {
    stubTable({ maintenanceTable: () => jsonResponse({ detail: "database down" }, 500) });
    renderAt(`${PAGE}/commits`);
    expect(await screen.findByText(/Could not load maintenance: database down/)).toBeInTheDocument();
  });

  it("shows the schema with partition spec sort order and spark ddl", async () => {
    stubTable();
    renderAt(`${PAGE}/schema`);
    const fields = await screen.findByRole("region", { name: "Schema" });
    expect(within(fields).getByText("struct<city: required string, zip: string>")).toBeInTheDocument();
    const spec = screen.getByRole("region", { name: "Partition spec" });
    expect(within(spec).getByText("placed_at_day")).toBeInTheDocument();
    expect(within(spec).getByText("placed_at")).toBeInTheDocument();
    const order = screen.getByRole("region", { name: "Sort order" });
    expect(within(order).getByText("nulls-first")).toBeInTheDocument();
    const ddl = screen.getByRole("region", { name: "DDL (Spark SQL)" });
    expect(ddl).toHaveTextContent("CREATE TABLE `iceberg`.`retail`.`orders`");
    expect(ddl).toHaveTextContent("`address` STRUCT<`city`: STRING NOT NULL, `zip`: STRING>");
  });

  it("has no snapshots tab: its old url opens the overview", async () => {
    stubTable();
    renderAt(`${PAGE}/snapshots`);
    await screen.findByText("Maintenance: managed");
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByRole("tab", { name: "Snapshots" })).not.toBeInTheDocument();
  });

  it("rename navigates to the new url", async () => {
    const user = userEvent.setup();
    const renamed = catalogTableFixture({ namespace: ["retail", "eu"], name: "orders_v2" });
    const calls = stubTable({
      extra: {
        [`POST ${TABLE}/rename`]: () =>
          jsonResponse({ catalog: "iceberg", namespace: ["retail", "eu"], name: "orders_v2" }),
        "GET /v1/catalogs/iceberg/namespaces/retail%1Feu/tables/orders_v2": () => jsonResponse(renamed),
      },
    });
    renderAt(`${PAGE}/schema`);
    await openAction(user, "Rename");
    const dialog = await screen.findByRole("dialog", { name: "Rename table" });
    await user.click(within(dialog).getByRole("button", { name: "Add level" }));
    await user.type(within(dialog).getByLabelText("Namespace level 2"), "eu");
    const name = within(dialog).getByLabelText("Name");
    await user.clear(name);
    await user.type(name, "orders_v2");
    await user.click(within(dialog).getByRole("button", { name: "Rename" }));

    expect(bodyOf(calls, "POST", `${TABLE}/rename`)).toEqual({
      target_namespace: ["retail", "eu"],
      target_name: "orders_v2",
    });
    expect(await screen.findByRole("heading", { level: 1, name: "orders_v2" })).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent(
      "/catalogs/iceberg/namespaces/retail%1Feu/tables/orders_v2/schema",
    );
    expect(callsTo(calls, "GET", TABLE)).toHaveLength(1);
  });

  it("the actions menu holds rename and delete only; properties are edited in the Properties tab", async () => {
    const user = userEvent.setup();
    stubTable();
    renderAt(PAGE);
    await user.click(await screen.findByRole("button", { name: "Actions" }));
    const items = await screen.findAllByRole("menuitem");
    expect(items.map((item) => item.textContent)).toEqual(["Rename", "Delete"]);
  });

  it("edit properties sends the loaded uuid and only the changes", async () => {
    const user = userEvent.setup();
    const calls = stubTable({
      extra: { [`PUT ${TABLE}/properties`]: () => jsonResponse(catalogTableFixture()) },
    });
    renderAt(`${PAGE}/properties`);
    await user.click(await screen.findByRole("button", { name: "Edit properties" }));
    const dialog = await screen.findByRole("dialog", { name: "Edit properties" });
    await user.click(within(dialog).getByRole("button", { name: "Remove owner" }));
    await user.click(within(dialog).getByRole("button", { name: "Save" }));
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(bodyOf(calls, "PUT", `${TABLE}/properties`)).toEqual({
      expected_uuid: "uuid-orders",
      updates: {},
      removals: ["owner"],
    });
  });

  it("properties conflict shows reload message", async () => {
    const user = userEvent.setup();
    stubTable({
      extra: {
        [`PUT ${TABLE}/properties`]: () =>
          jsonResponse({ detail: "table iceberg.retail.orders was replaced" }, 409),
      },
    });
    renderAt(`${PAGE}/properties`);
    await user.click(await screen.findByRole("button", { name: "Edit properties" }));
    const dialog = await screen.findByRole("dialog", { name: "Edit properties" });
    await user.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "This table changed since you loaded it, reload and try again.",
    );
    expect(within(dialog).getByRole("button", { name: "Reload" })).toBeInTheDocument();
  });

  it("delete goes to the namespace page", async () => {
    const user = userEvent.setup();
    const calls = stubTable({ extra: { [`DELETE ${TABLE}`]: () => new Response(null, { status: 204 }) } });
    renderAt(PAGE);
    await openAction(user, "Delete");
    const dialog = await screen.findByRole("alertdialog", { name: "Delete table" });
    expect(dialog).toHaveTextContent("iceberg / retail / orders");
    await user.type(within(dialog).getByLabelText(/Type orders to confirm/), "orders");
    await user.click(within(dialog).getByRole("button", { name: "Delete" }));
    expect(await screen.findByText("namespace page")).toBeInTheDocument();
    expect(callsTo(calls, "DELETE", TABLE)).toHaveLength(1);
    expect(callsTo(calls, "GET", TABLE)).toHaveLength(1);
  });

  it("never refetches the deleted table while the navigation is still pending", async () => {
    const user = userEvent.setup();
    const calls = stubTable({ extra: { [`DELETE ${TABLE}`]: () => new Response(null, { status: 204 }) } });
    renderAt(PAGE, <SuspendForever />);
    await openAction(user, "Delete");
    const dialog = await screen.findByRole("alertdialog", { name: "Delete table" });
    await user.type(within(dialog).getByLabelText(/Type orders to confirm/), "orders");
    await user.click(within(dialog).getByRole("button", { name: "Delete" }));
    await vi.waitFor(() => expect(callsTo(calls, "DELETE", TABLE)).toHaveLength(1));
    await settle();
    expect(callsTo(calls, "GET", TABLE)).toHaveLength(1);
  });

  it("falls back to Overview for an unknown tab segment", async () => {
    stubTable();
    renderAt(`${PAGE}/nonsense`);
    await screen.findByRole("region", { name: "Table" });
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
  });

  it("selects the tab named in the URL", async () => {
    stubTable();
    renderAt(`${PAGE}/properties`);
    expect(await screen.findByText("write.format.default")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Properties" })).toHaveAttribute("aria-selected", "true");
  });

  it("navigates to the commits route when the Commits tab is activated", async () => {
    const user = userEvent.setup();
    stubTable();
    renderAt(`${PAGE}/properties`);
    await screen.findByText("write.format.default");
    await user.click(screen.getByRole("tab", { name: "Commits" }));
    expect(await screen.findByText("No commits.")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Commits" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("location")).toHaveTextContent(`${PAGE}/commits`);
  });

  it("does not switch the page on a modified mousedown", async () => {
    stubTable();
    renderAt(`${PAGE}/properties`);
    await screen.findByText("write.format.default");
    fireEvent.mouseDown(screen.getByRole("tab", { name: "Commits" }), { button: 0, metaKey: true });
    expect(screen.getByRole("tab", { name: "Properties" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("location")).toHaveTextContent(`${PAGE}/properties`);
  });

  it("navigates when a tab is activated with the keyboard", async () => {
    const user = userEvent.setup();
    stubTable();
    renderAt(`${PAGE}/properties`);
    await screen.findByText("write.format.default");
    screen.getByRole("tab", { name: "Properties" }).focus();
    await user.keyboard("{ArrowRight}{ArrowRight}");
    expect(await screen.findByText("No maintenance runs yet.")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Maintenance" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("location")).toHaveTextContent(`${PAGE}/maintenance`);
  });

  it("missing table shows renamed-or-dropped state", async () => {
    stubTable({
      extra: { [`GET ${TABLE}`]: () => jsonResponse({ detail: "Table does not exist: retail.orders" }, 404) },
    });
    renderAt(`${PAGE}/commits`);
    expect(await screen.findByText(/may have been renamed or dropped/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Go to iceberg / retail" })).toHaveAttribute(
      "href",
      "/catalogs/iceberg/namespaces/retail",
    );
  });

  it("shows other catalog errors with their message", async () => {
    stubTable({ extra: { [`GET ${TABLE}`]: () => jsonResponse({ detail: "polaris unreachable" }, 502) } });
    renderAt(PAGE);
    expect(await screen.findByText(/Could not load table: polaris unreachable/)).toBeInTheDocument();
  });

  it("refetches the table when a properties save fails", async () => {
    const user = userEvent.setup();
    const calls = stubTable({
      extra: { [`PUT ${TABLE}/properties`]: () => jsonResponse({ detail: "Polaris is unreachable" }, 502) },
    });
    renderAt(`${PAGE}/properties`);
    await user.click(await screen.findByRole("button", { name: "Edit properties" }));
    const dialog = await screen.findByRole("dialog", { name: "Edit properties" });
    await user.click(within(dialog).getByRole("button", { name: "Remove owner" }));
    await user.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Polaris is unreachable");
    await vi.waitFor(() => expect(callsTo(calls, "GET", TABLE).length).toBeGreaterThan(1));
  });

  it("refetches the namespace's tables when a rename fails", async () => {
    const user = userEvent.setup();
    stubTable({
      extra: { [`POST ${TABLE}/rename`]: () => jsonResponse({ detail: "Polaris is unreachable" }, 502) },
    });
    const client = renderAt(PAGE);
    const invalidate = vi.spyOn(client, "invalidateQueries");
    await openAction(user, "Rename");
    const dialog = await screen.findByRole("dialog", { name: "Rename table" });
    const name = within(dialog).getByLabelText("Name");
    await user.clear(name);
    await user.type(name, "orders_v2");
    await user.click(within(dialog).getByRole("button", { name: "Rename" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Polaris is unreachable");
    await vi.waitFor(() =>
      expect(invalidate).toHaveBeenCalledWith({ queryKey: getListCatalogTablesQueryKey("iceberg", "retail") }),
    );
  });
});
