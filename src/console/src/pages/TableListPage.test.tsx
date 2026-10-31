import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TableApiResponse } from "../api/types";
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
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify(tables), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );
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
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(TABLES), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
  });

  it("loads the tables from the API and renders their full names", async () => {
    renderPage();

    expect(await screen.findByText("iceberg.inventory.orders")).toBeInTheDocument();
    expect(screen.getByText("iceberg.e2e.tm_e2e_regions")).toBeInTheDocument();
    expect(vi.mocked(fetch).mock.calls[0]?.[0]).toBe("/console/api/v1/tables");
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

  it("links each row to its table page", async () => {
    renderPage();

    const orders = await screen.findByRole("link", { name: "iceberg.inventory.orders" });
    const regions = screen.getByRole("link", { name: "iceberg.e2e.tm_e2e_regions" });
    expect(orders).toHaveAttribute("href", "/tables/uuid-orders");
    expect(regions).toHaveAttribute("href", "/tables/uuid-regions");
  });

  it("shows the API error detail when loading fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "database unavailable" }), {
          status: 503,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
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
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => {})));
    const { container } = renderPage();

    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0);
  });

  it("shows an empty state when no table matches", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("iceberg.inventory.orders");

    await user.type(screen.getByLabelText("Search"), "nothing-like-this");

    expect(screen.getByText("No tables match.")).toBeInTheDocument();
  });
});
