import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
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
});
