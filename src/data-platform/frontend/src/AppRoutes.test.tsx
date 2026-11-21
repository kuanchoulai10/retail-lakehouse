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
  it.each(["/tables/uuid-orders", "/tables/uuid-orders/commits", "/compaction-rounds"])(
    "a route that no longer exists renders not found: %s",
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

  it("renders the discovery policies page at /discovery-policies", async () => {
    stubCatalogApi({
      "GET /v1/discovery-policies": () => jsonResponse({ policies: [] }),
      "GET /v1/scanned-catalogs": () => jsonResponse({ catalogs: [] }),
    });
    renderAt("/discovery-policies");
    expect(await screen.findByRole("heading", { name: "Discovery policies", level: 1 })).toBeInTheDocument();
  });

  it("sends the old /discovery-rules bookmark to the discovery policies page", async () => {
    const calls = stubCatalogApi({
      "GET /v1/discovery-policies": () => jsonResponse({ policies: [] }),
      "GET /v1/scanned-catalogs": () => jsonResponse({ catalogs: [] }),
    });
    renderAt("/discovery-rules");
    expect(await screen.findByRole("heading", { name: "Discovery policies", level: 1 })).toBeInTheDocument();
    expect(calls.some((call) => call.path.startsWith("/v1/discovery-rules"))).toBe(false);
  });

  it("renders the platform settings page at /platform-settings", async () => {
    stubCatalogApi({ "GET /v1/platform-settings": () => jsonResponse({ groups: [] }) });
    renderAt("/platform-settings");
    expect(await screen.findByRole("heading", { name: "Platform settings", level: 1 })).toBeInTheDocument();
  });
});
