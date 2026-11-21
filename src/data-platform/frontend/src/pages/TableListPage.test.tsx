import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { beforeEach, describe, expect, it } from "vitest";
import type { TableApiResponse } from "../api/generated/model";
import { stubCatalogApi, type StubbedCall } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { TableListPage } from "./TableListPage";

function table(overrides: Partial<TableApiResponse>): TableApiResponse {
  return {
    uuid: "00000000-0000-0000-0000-000000000000",
    catalog: "iceberg",
    namespace: "inventory",
    table: "orders",
    status: "managed",
    priority: "P3",
    matched_rule_id: "dr-01m7s6c3tqee0rhg00xn5s97gw",
    matched_policy_id: "dp-01m7s6c3tqee0rhg00xn5s97gv",
    matched_policy_version: 1,
    operation_states: {},
    registered_at: "2026-10-30T10:00:00Z",
    updated_at: "2026-10-31T08:00:00Z",
    last_committed_at: "2026-10-31T07:45:00Z",
    last_discovered_at: "2026-10-31T08:10:00Z",
    ...overrides,
  };
}

const TABLES: TableApiResponse[] = [
  table({ uuid: "uuid-orders", namespace: "inventory", table: "orders" }),
  table({
    uuid: "uuid-regions",
    namespace: "e2e",
    table: "tm_e2e_regions",
    status: "unmanaged",
    matched_rule_id: null,
  }),
];

function stubTables(tables: TableApiResponse[]) {
  return stubCatalogApi({
    "GET /v1/tables": () => jsonResponse(tables),
  });
}

function rowNames(): string[] {
  return screen
    .getAllByRole("row")
    .slice(1)
    .map((row) => within(row).getAllByRole("link")[0]?.textContent ?? "");
}

// Each time column orders the rows differently, and one row's time is unknown in each, so a sort
// that ignored the column or misplaced the unknown time would show.
const SORTABLE: TableApiResponse[] = [
  table({
    uuid: "u-b",
    table: "b_table",
    last_committed_at: "2026-10-31T09:00:00Z",
    last_discovered_at: null,
  }),
  table({
    uuid: "u-a",
    table: "a_table",
    last_committed_at: "2026-10-31T07:00:00Z",
    last_discovered_at: "2026-10-31T10:00:00Z",
  }),
  table({
    uuid: "u-c",
    table: "c_table",
    last_committed_at: null,
    last_discovered_at: "2026-10-31T11:00:00Z",
  }),
  table({
    uuid: "u-d",
    table: "d_table",
    last_committed_at: "2026-10-31T08:00:00Z",
    last_discovered_at: "2026-10-31T09:30:00Z",
  }),
];

function renderPage(route = "/") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter([{ path: "/", element: <TableListPage /> }], { initialEntries: [route] });
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return router;
}

const WITH_DROPPED: TableApiResponse[] = [
  ...TABLES,
  table({ uuid: "uuid-gone", table: "gone", status: "dropped" }),
];

// The Status column header is a sort button too, so pick the filter by its id.
function statusFilter(): HTMLElement {
  const filter = screen.getAllByRole("button", { name: /Status/ }).find((button) => button.id === "status-filter");
  if (!filter) throw new Error("status filter not found");
  return filter;
}

async function toggleStatus(user: ReturnType<typeof userEvent.setup>, name: string) {
  await user.click(statusFilter());
  await user.click(await screen.findByRole("menuitemcheckbox", { name }));
  await user.keyboard("{Escape}");
}

describe("TableListPage", () => {
  let calls: StubbedCall[];

  beforeEach(() => {
    calls = stubTables(TABLES);
  });

  it("loads the tables from the API and renders their full names", async () => {
    renderPage();

    expect(await screen.findByText("iceberg.inventory.orders")).toBeInTheDocument();
    expect(screen.getByText("iceberg.e2e.tm_e2e_regions")).toBeInTheDocument();
    expect(calls.map((call) => call.path)).toContain("/v1/tables");
  });

  it("shows the status per row, with no rule column, selection or preset", async () => {
    renderPage();

    const managed = within((await screen.findByText("iceberg.inventory.orders")).closest("tr") as HTMLElement);
    expect(managed.getByText("Managed")).toHaveClass("bg-inverse-primary");
    expect(managed.queryByText(/Priority/)).not.toBeInTheDocument();
    const unmanaged = within(screen.getByText("iceberg.e2e.tm_e2e_regions").closest("tr") as HTMLElement);
    expect(unmanaged.getByText("Unmanaged")).toHaveClass("bg-surface-container-dim");
    expect(screen.queryByRole("columnheader", { name: /Rule/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: /Selection|Source preset/ })).not.toBeInTheDocument();
  });

  it("does not ask for the discovery policies or the old discovery rules", async () => {
    renderPage();
    await screen.findByText("iceberg.inventory.orders");

    expect(calls.filter((call) => call.path.startsWith("/v1/discovery-"))).toHaveLength(0);
  });

  it("hides dropped tables until Dropped is checked", async () => {
    const user = userEvent.setup();
    stubTables(WITH_DROPPED);
    renderPage();
    await screen.findByText("iceberg.inventory.orders");

    expect(screen.getByText("iceberg.e2e.tm_e2e_regions")).toBeInTheDocument();
    expect(screen.queryByText("iceberg.inventory.gone")).not.toBeInTheDocument();
    expect(statusFilter()).toHaveTextContent("Managed, Unmanaged");

    await toggleStatus(user, "Dropped");

    expect(screen.getByText("iceberg.inventory.gone")).toBeInTheDocument();
    expect(screen.getByText("iceberg.inventory.orders")).toBeInTheDocument();
  });

  it("combines any statuses, so each unchecked status hides its rows", async () => {
    const user = userEvent.setup();
    stubTables(WITH_DROPPED);
    renderPage();
    await screen.findByText("iceberg.inventory.orders");

    await toggleStatus(user, "Managed");
    expect(screen.queryByText("iceberg.inventory.orders")).not.toBeInTheDocument();
    expect(screen.getByText("iceberg.e2e.tm_e2e_regions")).toBeInTheDocument();

    await toggleStatus(user, "Dropped");
    expect(screen.getByText("iceberg.inventory.gone")).toBeInTheDocument();
    expect(screen.getByText("iceberg.e2e.tm_e2e_regions")).toBeInTheDocument();
    expect(screen.queryByText("iceberg.inventory.orders")).not.toBeInTheDocument();

    await toggleStatus(user, "Unmanaged");
    expect(screen.getByText("iceberg.inventory.gone")).toBeInTheDocument();
    expect(screen.queryByText("iceberg.e2e.tm_e2e_regions")).not.toBeInTheDocument();
  });

  it("keeps the url clean at the default and writes the selection back with replace", async () => {
    const user = userEvent.setup();
    stubTables(WITH_DROPPED);
    const router = renderPage();
    await screen.findByText("iceberg.inventory.orders");
    expect(router.state.location.search).toBe("");

    await toggleStatus(user, "Dropped");
    expect(router.state.location.search).toBe("?status=managed%2Cunmanaged%2Cdropped");
    expect(router.state.historyAction).toBe("REPLACE");

    await toggleStatus(user, "Managed");
    expect(router.state.location.search).toBe("?status=unmanaged%2Cdropped");

    await toggleStatus(user, "Dropped");
    await toggleStatus(user, "Managed");
    expect(router.state.location.search).toBe("");
    expect(router.state.historyAction).toBe("REPLACE");
  });

  it("keeps the other query parameters when it writes the selection", async () => {
    const user = userEvent.setup();
    const router = renderPage("/?foo=bar");
    await screen.findByText("iceberg.inventory.orders");

    await toggleStatus(user, "Dropped");

    expect(new URLSearchParams(router.state.location.search).get("foo")).toBe("bar");
  });

  it("reads the selection from the url", async () => {
    stubTables(WITH_DROPPED);
    renderPage("/?status=dropped");

    expect(await screen.findByText("iceberg.inventory.gone")).toBeInTheDocument();
    expect(screen.queryByText("iceberg.inventory.orders")).not.toBeInTheDocument();
    expect(screen.queryByText("iceberg.e2e.tm_e2e_regions")).not.toBeInTheDocument();
    expect(statusFilter()).toHaveTextContent("Dropped");
  });

  it("reads a comma separated selection from the url", async () => {
    stubTables(WITH_DROPPED);
    renderPage("/?status=managed,dropped");

    expect(await screen.findByText("iceberg.inventory.gone")).toBeInTheDocument();
    expect(screen.getByText("iceberg.inventory.orders")).toBeInTheDocument();
    expect(screen.queryByText("iceberg.e2e.tm_e2e_regions")).not.toBeInTheDocument();
  });

  it("ignores unknown statuses in the url", async () => {
    stubTables(WITH_DROPPED);
    renderPage("/?status=bogus,dropped");

    expect(await screen.findByText("iceberg.inventory.gone")).toBeInTheDocument();
    expect(screen.queryByText("iceberg.inventory.orders")).not.toBeInTheDocument();
  });

  it("falls back to the default when the url names no known status", async () => {
    stubTables(WITH_DROPPED);
    renderPage("/?status=bogus");

    expect(await screen.findByText("iceberg.inventory.orders")).toBeInTheDocument();
    expect(screen.queryByText("iceberg.inventory.gone")).not.toBeInTheDocument();
  });

  it("shows an explicit empty state, not every row, when no status is selected", async () => {
    stubTables(WITH_DROPPED);
    renderPage("/?status=");

    expect(await screen.findByText("No status selected.")).toBeInTheDocument();
    expect(screen.queryByText("iceberg.inventory.orders")).not.toBeInTheDocument();
    expect(screen.queryByText("iceberg.inventory.gone")).not.toBeInTheDocument();
    expect(statusFilter()).toHaveTextContent("None selected");
  });

  it("writes an empty status parameter when the last status is unchecked", async () => {
    const user = userEvent.setup();
    const router = renderPage();
    await screen.findByText("iceberg.inventory.orders");

    await toggleStatus(user, "Managed");
    await toggleStatus(user, "Unmanaged");

    expect(router.state.location.search).toBe("?status=");
    expect(screen.getByText("No status selected.")).toBeInTheDocument();
  });

  it("filters the rows by a substring of the full name", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("iceberg.inventory.orders");

    await user.type(screen.getByLabelText("Search"), "inventory.ord");

    expect(screen.getByText("iceberg.inventory.orders")).toBeInTheDocument();
    expect(screen.queryByText("iceberg.e2e.tm_e2e_regions")).not.toBeInTheDocument();
  });

  it("maintenance list links to the catalog path and dropped rows have no link", async () => {
    stubTables([
      ...TABLES,
      table({ uuid: "uuid-nested", namespace: "retail.eu", table: "sales" }),
      table({ uuid: "uuid-gone", table: "gone", status: "dropped" }),
    ]);
    renderPage("/?status=managed,unmanaged,dropped");

    const orders = await screen.findByRole("link", { name: "iceberg.inventory.orders" });
    const regions = screen.getByRole("link", { name: "iceberg.e2e.tm_e2e_regions" });
    const nested = screen.getByRole("link", { name: "iceberg.retail.eu.sales" });
    expect(orders).toHaveAttribute("href", "/catalogs/iceberg/namespaces/inventory/tables/orders");
    expect(regions).toHaveAttribute("href", "/catalogs/iceberg/namespaces/e2e/tables/tm_e2e_regions");
    expect(nested).toHaveAttribute("href", "/catalogs/iceberg/namespaces/retail%1Feu/tables/sales");
    expect(screen.getByText("iceberg.inventory.gone")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "iceberg.inventory.gone" })).not.toBeInTheDocument();
  });

  it("shows the API error detail when loading fails", async () => {
    stubCatalogApi({ "GET /v1/tables": () => jsonResponse({ detail: "database unavailable" }, 503) });
    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent("database unavailable");
  });

  it("sorts by name ascending by default", async () => {
    stubTables(SORTABLE);
    renderPage();
    await screen.findByText("iceberg.inventory.a_table");

    expect(rowNames()).toEqual([
      "iceberg.inventory.a_table",
      "iceberg.inventory.b_table",
      "iceberg.inventory.c_table",
      "iceberg.inventory.d_table",
    ]);
  });

  it("has Last commit and Last discovered columns and no Updated column", async () => {
    renderPage();
    await screen.findByText("iceberg.inventory.orders");

    const headers = screen.getAllByRole("columnheader").map((header) => header.textContent);
    expect(headers).toEqual(
      expect.arrayContaining([expect.stringMatching(/^Last commit/), expect.stringMatching(/^Last discovered/)]),
    );
    expect(screen.queryByRole("columnheader", { name: /Updated/ })).not.toBeInTheDocument();
  });

  it("shows both times as machine-readable timestamps", async () => {
    renderPage();
    const row = (await screen.findByText("iceberg.inventory.orders")).closest("tr") as HTMLElement;

    const times = [...row.querySelectorAll("time")].map((time) => time.getAttribute("dateTime"));
    expect(times).toEqual(["2026-10-31T07:45:00Z", "2026-10-31T08:10:00Z"]);
  });

  it("shows a dash for a time that is not known", async () => {
    stubTables([table({ uuid: "u-new", table: "fresh", last_committed_at: null, last_discovered_at: null })]);
    renderPage();
    const row = within((await screen.findByText("iceberg.inventory.fresh")).closest("tr") as HTMLElement);

    expect(row.getAllByText("—")).toHaveLength(2);
  });

  it("clicking Last commit sorts newest first then oldest first, unknown times last", async () => {
    const user = userEvent.setup();
    stubTables(SORTABLE);
    renderPage();
    await screen.findByText("iceberg.inventory.a_table");

    await user.click(screen.getByRole("button", { name: /Last commit/ }));
    expect(rowNames()).toEqual([
      "iceberg.inventory.b_table",
      "iceberg.inventory.d_table",
      "iceberg.inventory.a_table",
      "iceberg.inventory.c_table",
    ]);

    await user.click(screen.getByRole("button", { name: /Last commit/ }));
    expect(rowNames()).toEqual([
      "iceberg.inventory.a_table",
      "iceberg.inventory.d_table",
      "iceberg.inventory.b_table",
      "iceberg.inventory.c_table",
    ]);
  });

  it("clicking Last discovered sorts newest first then oldest first, unknown times last", async () => {
    const user = userEvent.setup();
    stubTables(SORTABLE);
    renderPage();
    await screen.findByText("iceberg.inventory.a_table");

    await user.click(screen.getByRole("button", { name: /Last discovered/ }));
    expect(rowNames()).toEqual([
      "iceberg.inventory.c_table",
      "iceberg.inventory.a_table",
      "iceberg.inventory.d_table",
      "iceberg.inventory.b_table",
    ]);

    await user.click(screen.getByRole("button", { name: /Last discovered/ }));
    expect(rowNames()).toEqual([
      "iceberg.inventory.d_table",
      "iceberg.inventory.a_table",
      "iceberg.inventory.c_table",
      "iceberg.inventory.b_table",
    ]);
  });

  it("shows skeleton rows in a busy container while loading", () => {
    stubCatalogApi({ "GET /v1/tables": () => new Promise<Response>(() => {}) });
    renderPage();

    expect(document.querySelector('[aria-busy="true"]')).not.toBeNull();
    expect(document.querySelectorAll('[aria-busy="true"] .animate-pulse').length).toBeGreaterThan(0);
  });

  it("shows an empty state when no table matches", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("iceberg.inventory.orders");

    await user.type(screen.getByLabelText("Search"), "nothing-like-this");

    expect(screen.getByText("No tables match.")).toBeInTheDocument();
  });
});
