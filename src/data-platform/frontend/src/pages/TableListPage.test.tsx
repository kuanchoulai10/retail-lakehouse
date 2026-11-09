import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
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
    status: "active",
    selection: "auto",
    settings: null,
    matched_rule_id: "rule-1",
    source_preset_id: "default",
    operation_states: {},
    registered_at: "2026-10-30T10:00:00Z",
    updated_at: "2026-10-31T08:00:00Z",
    ...overrides,
  };
}

const TABLES: TableApiResponse[] = [
  table({ uuid: "uuid-orders", namespace: "inventory", table: "orders" }),
  table({
    uuid: "uuid-regions",
    namespace: "e2e",
    table: "tm_e2e_regions",
    status: "paused",
    selection: "manual",
    source_preset_id: "nightly",
  }),
];

function stubTables(tables: TableApiResponse[]) {
  return stubCatalogApi({ "GET /v1/tables": () => jsonResponse(tables) });
}

function rowNames(): string[] {
  return screen
    .getAllByRole("row")
    .slice(1)
    .map((row) => within(row).getByRole("link").textContent ?? "");
}

const SORTABLE: TableApiResponse[] = [
  table({ uuid: "u-b", table: "b_table", updated_at: "2026-10-31T09:00:00Z" }),
  table({ uuid: "u-a", table: "a_table", updated_at: "2026-10-31T07:00:00Z" }),
  table({ uuid: "u-c", table: "c_table", updated_at: "2026-10-31T08:00:00Z" }),
];

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <TableListPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
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
    expect(calls[0]?.path).toBe("/v1/tables");
  });

  it("shows status, selection and source preset per row", async () => {
    renderPage();

    const row = (await screen.findByText("iceberg.e2e.tm_e2e_regions")).closest("tr");
    expect(row).not.toBeNull();
    const cells = within(row as HTMLElement);
    expect(cells.getByText("Paused")).toBeInTheDocument();
    expect(cells.getByText("manual")).toBeInTheDocument();
    expect(cells.getByText("nightly")).toBeInTheDocument();
  });

  it("filters the rows by status", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("iceberg.inventory.orders");

    await user.click(screen.getByRole("combobox", { name: "Status" }));
    await user.click(await screen.findByRole("option", { name: "Paused" }));

    expect(screen.queryByText("iceberg.inventory.orders")).not.toBeInTheDocument();
    expect(screen.getByText("iceberg.e2e.tm_e2e_regions")).toBeInTheDocument();
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
    renderPage();

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
    ]);
  });

  it("clicking the Updated header sorts by updated_at descending then ascending", async () => {
    const user = userEvent.setup();
    stubTables(SORTABLE);
    renderPage();
    await screen.findByText("iceberg.inventory.a_table");

    await user.click(screen.getByRole("button", { name: /Updated/ }));
    expect(rowNames()).toEqual([
      "iceberg.inventory.b_table",
      "iceberg.inventory.c_table",
      "iceberg.inventory.a_table",
    ]);

    await user.click(screen.getByRole("button", { name: /Updated/ }));
    expect(rowNames()).toEqual([
      "iceberg.inventory.a_table",
      "iceberg.inventory.c_table",
      "iceberg.inventory.b_table",
    ]);
  });

  it("shows skeleton rows in a busy container while loading", () => {
    stubCatalogApi({ "GET /v1/tables": () => new Promise<Response>(() => {}) });
    const { container } = renderPage();

    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
    expect(container.querySelectorAll('[aria-busy="true"] .animate-pulse').length).toBeGreaterThan(0);
  });

  it("shows an empty state when no table matches", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("iceberg.inventory.orders");

    await user.type(screen.getByLabelText("Search"), "nothing-like-this");

    expect(screen.getByText("No tables match.")).toBeInTheDocument();
  });
});
