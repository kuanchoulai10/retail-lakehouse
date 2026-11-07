import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";
import type { ViewApiResponse } from "../api/catalogTypes";
import { callsTo, stubCatalogApi } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { ViewPage } from "./ViewPage";

const VIEW = "/v1/catalogs/iceberg/namespaces/retail/views/orders_v";

function view(): ViewApiResponse {
  return {
    catalog: "iceberg",
    namespace: ["retail"],
    name: "orders_v",
    uuid: "uuid-view",
    location: "s3://warehouse/retail/orders_v",
    sql: "SELECT id FROM retail.orders",
    dialect: "spark",
    default_namespace: ["retail"],
    current_version_id: 2,
    schema: { schema_id: 0, fields: [{ id: 1, name: "id", type: "long", required: false, doc: null }] },
    versions: [
      { version_id: 1, timestamp_ms: 1_700_000_000_000, sql: "SELECT * FROM retail.orders" },
      { version_id: 2, timestamp_ms: 1_700_000_100_000, sql: "SELECT id FROM retail.orders" },
    ],
    properties: { comment: "ids only" },
  };
}

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/catalogs/:catalog/namespaces/:namespace" element={<p>namespace page</p>} />
          <Route path="/catalogs/:catalog/namespaces/:namespace/views/:view" element={<ViewPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ViewPage", { timeout: 15_000 }, () => {
  it("view page shows sql and only delete", async () => {
    const user = userEvent.setup();
    stubCatalogApi({ [`GET ${VIEW}`]: () => jsonResponse(view()) });
    renderAt("/catalogs/iceberg/namespaces/retail/views/orders_v");
    const sql = await screen.findByRole("region", { name: "SQL" });
    expect(within(sql).getByText("SELECT id FROM retail.orders")).toBeInTheDocument();
    expect(within(sql).getByText("spark")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Schema" })).toHaveTextContent("long");
    const versions = screen.getByRole("region", { name: "Versions" });
    expect(within(versions).getAllByRole("row")[1]).toHaveTextContent("Current");
    expect(screen.getByRole("region", { name: "Properties" })).toHaveTextContent("ids only");
    expect(screen.queryByRole("tab")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Actions" }));
    const items = await screen.findAllByRole("menuitem");
    expect(items.map((item) => item.textContent)).toEqual(["Delete"]);
  });

  it("deletes the view and goes to the namespace page", async () => {
    const user = userEvent.setup();
    const calls = stubCatalogApi({
      [`GET ${VIEW}`]: () => jsonResponse(view()),
      [`DELETE ${VIEW}`]: () => new Response(null, { status: 204 }),
    });
    renderAt("/catalogs/iceberg/namespaces/retail/views/orders_v");
    await user.click(await screen.findByRole("button", { name: "Actions" }));
    await user.click(await screen.findByRole("menuitem", { name: "Delete" }));
    const dialog = await screen.findByRole("dialog", { name: "Delete view" });
    await user.type(within(dialog).getByLabelText(/Type orders_v to confirm/), "orders_v");
    await user.click(within(dialog).getByRole("button", { name: "Delete" }));
    expect(await screen.findByText("namespace page")).toBeInTheDocument();
    expect(callsTo(calls, "GET", VIEW)).toHaveLength(1);
  });

  it("shows a missing view with a link to its namespace", async () => {
    stubCatalogApi({ [`GET ${VIEW}`]: () => jsonResponse({ detail: "View does not exist" }, 404) });
    renderAt("/catalogs/iceberg/namespaces/retail/views/orders_v");
    expect(await screen.findByText(/may have been renamed or dropped/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Go to iceberg / retail" })).toHaveAttribute(
      "href",
      "/catalogs/iceberg/namespaces/retail",
    );
  });
});
