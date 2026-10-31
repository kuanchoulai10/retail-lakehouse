import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { jsonResponse, metadataFixture, tableFixture } from "../test/fixtures";
import { TablePage } from "./TablePage";

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/tables/:uuid/:tab?" element={<TablePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function stubFetch(metadata: () => Response) {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (url.endsWith("/metadata")) return Promise.resolve(metadata());
      if (url.endsWith("/v1/tables/uuid-orders")) return Promise.resolve(jsonResponse(tableFixture()));
      if (url.includes("/commits")) return Promise.resolve(jsonResponse({ items: [], truncated: false }));
      return Promise.resolve(jsonResponse([]));
    }),
  );
}

describe("TablePage", () => {
  beforeEach(() => {
    stubFetch(() => jsonResponse(metadataFixture()));
  });

  it("falls back to Overview for an unknown tab segment", async () => {
    renderAt("/tables/uuid-orders/nonsense");
    expect(await screen.findByText("iceberg.inventory.orders")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
  });

  it("navigates to the commits route when the Commits tab is activated", async () => {
    const user = userEvent.setup();
    renderAt("/tables/uuid-orders/properties");
    await screen.findByText("iceberg.inventory.orders");
    await user.click(screen.getByRole("tab", { name: "Commits" }));
    expect(await screen.findByText("No commits.")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Commits" })).toHaveAttribute("aria-selected", "true");
  });

  it("navigates when a tab is activated with the keyboard", async () => {
    const user = userEvent.setup();
    renderAt("/tables/uuid-orders/properties");
    await screen.findByText("iceberg.inventory.orders");
    screen.getByRole("tab", { name: "Properties" }).focus();
    await user.keyboard("{ArrowLeft}");
    expect(await screen.findByText("No maintenance runs yet.")).toBeInTheDocument();
  });

  it("selects the tab named in the URL", async () => {
    renderAt("/tables/uuid-orders/properties");
    expect(await screen.findByText("write.format.default")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Properties" })).toHaveAttribute("aria-selected", "true");
  });

  it("shows not-in-catalog notice when metadata answers 404", async () => {
    stubFetch(() =>
      jsonResponse({ detail: "table iceberg.inventory.orders is not in the catalog" }, 404),
    );
    renderAt("/tables/uuid-orders/commits");
    expect(await screen.findByText(/is not in the catalog/)).toBeInTheDocument();
    expect(screen.getByText("iceberg.inventory.orders")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
  });
});
