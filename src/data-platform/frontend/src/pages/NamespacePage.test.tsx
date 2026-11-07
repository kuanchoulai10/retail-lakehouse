import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";
import type { TableIdentifierApiResponse } from "../api/catalogTypes";
import { bodyOf, callsTo, stubCatalogApi, type StubHandler } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { NamespacePage } from "./NamespacePage";

const NS = "/v1/catalogs/iceberg/namespaces/retail";

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/catalogs/:catalog" element={<p>catalog page</p>} />
          <Route path="/catalogs/:catalog/namespaces/:namespace" element={<NamespacePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function id(name: string): TableIdentifierApiResponse {
  return { catalog: "iceberg", namespace: ["retail"], name };
}

function stubNamespace(extra: Record<string, StubHandler> = {}) {
  return stubCatalogApi({
    [`GET ${NS}`]: () =>
      jsonResponse({
        catalog: "iceberg",
        namespace: ["retail"],
        properties: { owner: "kc", location: "s3://w/retail" },
      }),
    "GET /v1/catalogs/iceberg/namespaces?parent=retail": () =>
      jsonResponse([{ catalog: "iceberg", namespace: ["retail", "eu"] }]),
    [`GET ${NS}/tables`]: () => jsonResponse([id("orders")]),
    [`GET ${NS}/views`]: () => jsonResponse([id("orders_v")]),
    [`GET ${NS}/generic-tables`]: () => jsonResponse([id("events")]),
    ...extra,
  });
}

async function openAction(user: ReturnType<typeof userEvent.setup>, label: string) {
  await user.click(screen.getByRole("button", { name: "Actions" }));
  await user.click(await screen.findByRole("menuitem", { name: label }));
}

describe("NamespacePage", () => {
  it("namespace page lists tables views and generic tables with a type column", async () => {
    stubNamespace();
    renderAt("/catalogs/iceberg/namespaces/retail");
    const objects = await screen.findByRole("region", { name: "Tables and views" });
    expect(within(objects).getByRole("columnheader", { name: "Type" })).toBeInTheDocument();
    expect(await within(objects).findByRole("row", { name: /orders_v/ })).toHaveTextContent("View");
    expect(within(objects).getByRole("row", { name: /^orders Table/ })).toBeInTheDocument();
    expect(within(objects).getByRole("row", { name: /events/ })).toHaveTextContent("Generic table");
    expect(within(objects).getByRole("link", { name: "orders" })).toHaveAttribute(
      "href",
      "/catalogs/iceberg/namespaces/retail/tables/orders",
    );
    expect(within(objects).getByRole("link", { name: "orders_v" })).toHaveAttribute(
      "href",
      "/catalogs/iceberg/namespaces/retail/views/orders_v",
    );
    expect(within(objects).getByRole("link", { name: "events" })).toHaveAttribute(
      "href",
      "/catalogs/iceberg/namespaces/retail/generic-tables/events",
    );

    const children = screen.getByRole("region", { name: "Namespaces" });
    expect(within(children).getByRole("link", { name: "eu" })).toHaveAttribute(
      "href",
      "/catalogs/iceberg/namespaces/retail%1Feu",
    );
    const properties = screen.getByRole("region", { name: "Properties" });
    expect(within(properties).getByText("owner")).toBeInTheDocument();
  });

  it("shows breadcrumbs that link every parent of a nested namespace", async () => {
    const nested = "/v1/catalogs/iceberg/namespaces/retail%1Feu";
    stubCatalogApi({
      [`GET ${nested}`]: () => jsonResponse({ catalog: "iceberg", namespace: ["retail", "eu"], properties: {} }),
      "GET /v1/catalogs/iceberg/namespaces?parent=retail%1Feu": () => jsonResponse([]),
      [`GET ${nested}/tables`]: () => jsonResponse([]),
      [`GET ${nested}/views`]: () => jsonResponse([]),
      [`GET ${nested}/generic-tables`]: () => jsonResponse([]),
    });
    renderAt("/catalogs/iceberg/namespaces/retail%1Feu");
    const crumbs = await screen.findByRole("navigation", { name: "Breadcrumb" });
    expect(within(crumbs).getByRole("link", { name: "Catalogs" })).toHaveAttribute("href", "/catalogs");
    expect(within(crumbs).getByRole("link", { name: "iceberg" })).toHaveAttribute("href", "/catalogs/iceberg");
    expect(within(crumbs).getByRole("link", { name: "retail" })).toHaveAttribute(
      "href",
      "/catalogs/iceberg/namespaces/retail",
    );
    expect(within(crumbs).getByText("eu")).toHaveAttribute("aria-current", "page");
  });

  it("deleting a non-empty namespace shows the polaris message", async () => {
    const user = userEvent.setup();
    stubNamespace({
      [`DELETE ${NS}`]: () => jsonResponse({ detail: "Namespace retail is not empty" }, 409),
    });
    renderAt("/catalogs/iceberg/namespaces/retail");
    await screen.findByRole("region", { name: "Tables and views" });
    await openAction(user, "Delete");
    const dialog = screen.getByRole("dialog");
    await user.type(within(dialog).getByLabelText(/to confirm/i), "retail");
    await user.click(within(dialog).getByRole("button", { name: "Delete" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Namespace retail is not empty");
    expect(within(dialog).getByRole("alert")).not.toHaveTextContent(/reload/i);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("deleting an empty namespace goes to its parent", async () => {
    const user = userEvent.setup();
    stubNamespace({ [`DELETE ${NS}`]: () => new Response(null, { status: 204 }) });
    renderAt("/catalogs/iceberg/namespaces/retail");
    await screen.findByRole("region", { name: "Tables and views" });
    await openAction(user, "Delete");
    await user.type(screen.getByLabelText(/to confirm/i), "retail");
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(await screen.findByText("catalog page")).toBeInTheDocument();
  });

  it("edits properties by sending updates and removals", async () => {
    const user = userEvent.setup();
    const calls = stubNamespace({
      [`PUT ${NS}/properties`]: () =>
        jsonResponse({ catalog: "iceberg", namespace: ["retail"], properties: { owner: "ops" } }),
    });
    renderAt("/catalogs/iceberg/namespaces/retail");
    await screen.findByRole("region", { name: "Tables and views" });
    await openAction(user, "Edit properties");
    const dialog = screen.getByRole("dialog");
    const ownerValue = within(dialog).getByLabelText("Value of owner");
    await user.clear(ownerValue);
    await user.type(ownerValue, "ops");
    await user.click(within(dialog).getByRole("button", { name: "Remove location" }));
    await user.click(within(dialog).getByRole("button", { name: "Save" }));
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(bodyOf(calls, "PUT", `${NS}/properties`)).toEqual({
      updates: { owner: "ops" },
      removals: ["location"],
    });
    expect(callsTo(calls, "GET", NS).length).toBeGreaterThan(1);
  });

  it("creates a view with the spark dialect by default", async () => {
    const user = userEvent.setup();
    const calls = stubNamespace({ [`POST ${NS}/views`]: () => jsonResponse({}, 201) });
    renderAt("/catalogs/iceberg/namespaces/retail");
    const objects = await screen.findByRole("region", { name: "Tables and views" });
    await user.click(within(objects).getByRole("button", { name: "New table or view" }));
    await user.click(screen.getByRole("button", { name: "View" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByLabelText("Dialect")).toHaveValue("spark");
    await user.type(within(dialog).getByLabelText("Name"), "big_orders");
    await user.type(within(dialog).getByLabelText("SQL"), "SELECT * FROM orders");
    await user.click(within(dialog).getByRole("button", { name: "Create" }));
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(bodyOf(calls, "POST", `${NS}/views`)).toEqual({
      name: "big_orders",
      sql: "SELECT * FROM orders",
      dialect: "spark",
    });
    expect(callsTo(calls, "GET", `${NS}/views`).length).toBeGreaterThan(1);
  });

  it("creates a table with its schema fields and partition", async () => {
    const user = userEvent.setup();
    const calls = stubNamespace({ [`POST ${NS}/tables`]: () => jsonResponse({}, 201) });
    renderAt("/catalogs/iceberg/namespaces/retail");
    const objects = await screen.findByRole("region", { name: "Tables and views" });
    await user.click(within(objects).getByRole("button", { name: "New table or view" }));
    await user.click(screen.getByRole("button", { name: "Table" }));
    const dialog = screen.getByRole("dialog");
    await user.type(within(dialog).getByLabelText("Name"), "payments");
    await user.type(within(dialog).getByLabelText("Field 1 name"), "id");
    await user.type(within(dialog).getByLabelText("Field 1 type"), "long");
    await user.click(within(dialog).getByRole("button", { name: "Add field" }));
    await user.type(within(dialog).getByLabelText("Field 2 name"), "paid_at");
    await user.type(within(dialog).getByLabelText("Field 2 type"), "timestamptz");
    await user.click(within(dialog).getByLabelText("Field 2 required"));
    await user.click(within(dialog).getByRole("button", { name: "Add partition" }));
    await user.type(within(dialog).getByLabelText("Partition 1 column"), "paid_at");
    await user.click(within(dialog).getByRole("combobox", { name: "Partition 1 transform" }));
    await user.click(await screen.findByRole("option", { name: "day" }));
    await user.click(within(dialog).getByRole("button", { name: "Create" }));
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(bodyOf(calls, "POST", `${NS}/tables`)).toEqual({
      name: "payments",
      schema_fields: [
        { name: "id", type: "long", required: true },
        { name: "paid_at", type: "timestamptz", required: false },
      ],
      partition_fields: [{ source_column: "paid_at", transform: "day" }],
      properties: {},
    });
    expect(callsTo(calls, "GET", `${NS}/tables`).length).toBeGreaterThan(1);
  });

  it("creates a generic table", async () => {
    const user = userEvent.setup();
    const calls = stubNamespace({ [`POST ${NS}/generic-tables`]: () => jsonResponse({}, 201) });
    renderAt("/catalogs/iceberg/namespaces/retail");
    const objects = await screen.findByRole("region", { name: "Tables and views" });
    await user.click(within(objects).getByRole("button", { name: "New table or view" }));
    await user.click(screen.getByRole("button", { name: "Generic table" }));
    const dialog = screen.getByRole("dialog");
    await user.type(within(dialog).getByLabelText("Name"), "clicks");
    await user.type(within(dialog).getByLabelText("Format"), "delta");
    await user.type(within(dialog).getByLabelText(/Base location/), "s3://w/clicks");
    await user.click(within(dialog).getByRole("button", { name: "Create" }));
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(bodyOf(calls, "POST", `${NS}/generic-tables`)).toEqual({
      name: "clicks",
      format: "delta",
      base_location: "s3://w/clicks",
      properties: {},
    });
  });

  it("deletes a view from the list and refetches the views", async () => {
    const user = userEvent.setup();
    const calls = stubNamespace({ [`DELETE ${NS}/views/orders_v`]: () => new Response(null, { status: 204 }) });
    renderAt("/catalogs/iceberg/namespaces/retail");
    const objects = await screen.findByRole("region", { name: "Tables and views" });
    await within(objects).findByRole("link", { name: "orders_v" });
    await user.click(within(objects).getByRole("button", { name: "Delete orders_v" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByRole("heading", { name: "Delete view" })).toBeInTheDocument();
    await user.type(within(dialog).getByLabelText(/to confirm/i), "orders_v");
    await user.click(within(dialog).getByRole("button", { name: "Delete" }));
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(callsTo(calls, "DELETE", `${NS}/views/orders_v`)).toHaveLength(1);
    expect(callsTo(calls, "GET", `${NS}/views`).length).toBeGreaterThan(1);
  });
});
