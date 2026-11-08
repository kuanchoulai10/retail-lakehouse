import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { catalogTableFixture, stubCatalogApi } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { TablePage } from "./TablePage";

const LONG_NAME = "orders_with_a_very_long_name_that_runs_to_sixty_characters_x";

describe("TablePage on a phone", () => {
  const desktopWidth = window.innerWidth;

  beforeEach(() => {
    window.innerWidth = 390;
    window.dispatchEvent(new Event("resize"));
  });

  afterEach(() => {
    window.innerWidth = desktopWidth;
    window.dispatchEvent(new Event("resize"));
  });

  it("wraps a long table name so the full name is readable", async () => {
    expect(LONG_NAME).toHaveLength(60);
    stubCatalogApi({
      [`GET /v1/catalogs/iceberg/namespaces/retail/tables/${LONG_NAME}`]: () =>
        jsonResponse(catalogTableFixture({ name: LONG_NAME })),
      "GET /v1/table-discovery-settings/catalogs": () => jsonResponse({ catalogs: [] }),
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[`/catalogs/iceberg/namespaces/retail/tables/${LONG_NAME}`]}>
          <Routes>
            <Route path="/catalogs/:catalog/namespaces/:namespace/tables/:table/:tab?" element={<TablePage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    const title = await screen.findByRole("heading", { level: 1, name: LONG_NAME });
    expect(title).toHaveClass("[overflow-wrap:anywhere]");
    expect(title).toHaveTextContent(LONG_NAME);
  });
});
