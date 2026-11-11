import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";
import { stubCatalogApi } from "../test/catalogApiStub";
import { jsonResponse, policyContentFixture } from "../test/fixtures";
import { PolicyVersionPage } from "./PolicyVersionPage";

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/policies/:name/versions/:version" element={<PolicyVersionPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("PolicyVersionPage", () => {
  it("shows one saved version read only", async () => {
    const content = policyContentFixture();
    stubCatalogApi({
      "GET /v1/maintenance-policies/nightly/versions/2": () =>
        jsonResponse({
          ...content,
          name: "nightly",
          version: 2,
          dry_run: true,
          created_at: "2026-11-05T09:00:00Z",
          operations: { ...content.operations, remove_orphan_files: { ...content.operations.remove_orphan_files, enabled: false } },
        }),
    });
    renderAt("/policies/nightly/versions/2");
    expect(await screen.findByRole("heading", { level: 1, name: "nightly v2" })).toBeInTheDocument();
    const orphans = screen.getByRole("region", { name: "Remove orphan files" });
    expect(within(orphans).getByText("Off")).toBeInTheDocument();
    const data = screen.getByRole("region", { name: "Rewrite data files" });
    expect(within(data).getByText("Reducible files at least 5")).toBeInTheDocument();
    expect(screen.getByText("On: nothing is started")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Save|Edit/ })).not.toBeInTheDocument();
  });

  it("says when the version does not exist", async () => {
    stubCatalogApi({
      "GET /v1/maintenance-policies/nightly/versions/9": () => jsonResponse({ detail: "version 9 of nightly not found" }, 404),
    });
    renderAt("/policies/nightly/versions/9");
    expect(await screen.findByText("Could not load nightly v9: version 9 of nightly not found")).toBeInTheDocument();
  });
});
