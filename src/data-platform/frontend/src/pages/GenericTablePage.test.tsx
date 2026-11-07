import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";
import { callsTo, stubCatalogApi } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { GenericTablePage } from "./GenericTablePage";

const GENERIC = "/v1/catalogs/iceberg/namespaces/retail/generic-tables/events";

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/catalogs/:catalog/namespaces/:namespace" element={<p>namespace page</p>} />
          <Route
            path="/catalogs/:catalog/namespaces/:namespace/generic-tables/:name"
            element={<GenericTablePage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("GenericTablePage", { timeout: 15_000 }, () => {
  it("shows format location doc and properties with only delete", async () => {
    const user = userEvent.setup();
    stubCatalogApi({
      [`GET ${GENERIC}`]: () =>
        jsonResponse({
          catalog: "iceberg",
          namespace: ["retail"],
          name: "events",
          format: "delta",
          base_location: "s3://warehouse/retail/events",
          doc: "raw click events",
          properties: { owner: "web" },
        }),
    });
    renderAt("/catalogs/iceberg/namespaces/retail/generic-tables/events");
    const overview = await screen.findByRole("region", { name: "Overview" });
    expect(within(overview).getByText("delta")).toBeInTheDocument();
    expect(within(overview).getByText("s3://warehouse/retail/events")).toBeInTheDocument();
    expect(within(overview).getByText("raw click events")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Properties" })).toHaveTextContent("web");

    await user.click(screen.getByRole("button", { name: "Actions" }));
    const items = await screen.findAllByRole("menuitem");
    expect(items.map((item) => item.textContent)).toEqual(["Delete"]);
  });

  it("deletes the generic table and goes to the namespace page", async () => {
    const user = userEvent.setup();
    const calls = stubCatalogApi({
      [`GET ${GENERIC}`]: () =>
        jsonResponse({
          catalog: "iceberg",
          namespace: ["retail"],
          name: "events",
          format: "delta",
          base_location: null,
          doc: null,
          properties: {},
        }),
      [`DELETE ${GENERIC}`]: () => new Response(null, { status: 204 }),
    });
    renderAt("/catalogs/iceberg/namespaces/retail/generic-tables/events");
    await user.click(await screen.findByRole("button", { name: "Actions" }));
    await user.click(await screen.findByRole("menuitem", { name: "Delete" }));
    const dialog = await screen.findByRole("dialog", { name: "Delete generic table" });
    await user.type(within(dialog).getByLabelText(/Type events to confirm/), "events");
    await user.click(within(dialog).getByRole("button", { name: "Delete" }));
    expect(await screen.findByText("namespace page")).toBeInTheDocument();
    expect(callsTo(calls, "GET", GENERIC)).toHaveLength(1);
  });
});
