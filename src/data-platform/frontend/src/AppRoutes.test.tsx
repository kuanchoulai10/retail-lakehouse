import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { jsonResponse } from "./test/fixtures";
import { AppRoutes } from "./AppRoutes";
import { stubCatalogApi } from "./test/catalogApiStub";

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AppRoutes", () => {
  it.each(["/tables/uuid-orders", "/tables/uuid-orders/commits"])(
    "old tables uuid route renders not found: %s",
    (path) => {
      const calls = stubCatalogApi({});
      renderAt(path);
      expect(screen.getByRole("heading", { name: "Page not found" })).toBeInTheDocument();
      expect(calls).toEqual([]);
    },
  );

  it("renders the policies page at /policies", async () => {
    stubCatalogApi({ "GET /v1/maintenance-policies": () => jsonResponse({ policies: [] }) });
    renderAt("/policies");
    expect(await screen.findByRole("heading", { name: "Maintenance policies", level: 1 })).toBeInTheDocument();
  });

  it("renders the platform settings page at /platform-settings", async () => {
    stubCatalogApi({ "GET /v1/platform-settings": () => jsonResponse({ groups: [] }) });
    renderAt("/platform-settings");
    expect(await screen.findByRole("heading", { name: "Platform settings", level: 1 })).toBeInTheDocument();
  });

  it("renders the compaction rounds page at /compaction-rounds", async () => {
    stubCatalogApi({ "GET /v1/compaction-rounds?limit=50": () => jsonResponse([]) });
    renderAt("/compaction-rounds");
    expect(await screen.findByRole("heading", { name: "Compaction rounds", level: 1 })).toBeInTheDocument();
  });
});
