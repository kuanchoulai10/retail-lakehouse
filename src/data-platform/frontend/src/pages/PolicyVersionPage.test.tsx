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
          remove_orphan_files: null,
        }),
    });
    renderAt("/policies/nightly/versions/2");
    expect(await screen.findByRole("heading", { level: 1, name: "nightly v2" })).toBeInTheDocument();
    const orphans = screen.getByRole("region", { name: "Remove orphan files" });
    expect(within(orphans).getByText("Not in this policy")).toBeInTheDocument();
    const data = screen.getByRole("region", { name: "Rewrite data files" });
    expect(within(data).getByText("Reducible files at most 5, per partition")).toBeInTheDocument();
    expect(within(data).getByText("Min input files: 2")).toBeInTheDocument();
    const manifests = screen.getByRole("region", { name: "Rewrite manifests" });
    expect(within(manifests).getByText("Small manifests at most 5")).toBeInTheDocument();
    expect(within(manifests).getByText("Procedure defaults")).toBeInTheDocument();
    const snapshots = screen.getByRole("region", { name: "Expire snapshots" });
    expect(within(snapshots).getByText("Keep at least 10 snapshots")).toBeInTheDocument();
    expect(within(snapshots).getByText("Expire snapshots older than 1 d")).toBeInTheDocument();
    const facts = screen.getByRole("region", { name: "Policy" });
    expect(within(facts).getByText("Every 1 h, and 5 min after a commit")).toBeInTheDocument();
    expect(within(facts).getByText("On. Scheduled checks record what would run and start nothing; a manual run still runs.")).toBeInTheDocument();
    expect(within(facts).queryByText(/priority/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Save|Edit/ })).not.toBeInTheDocument();
  });

  it("says a retention value the policy leaves out falls to the table", async () => {
    const content = policyContentFixture();
    stubCatalogApi({
      "GET /v1/maintenance-policies/nightly/versions/3": () =>
        jsonResponse({
          ...content,
          name: "nightly",
          version: 3,
          created_at: "2026-11-05T09:00:00Z",
          expire_snapshots: { target: { min_snapshots_to_keep: null, max_snapshot_age_seconds: 604800 }, options: null },
        }),
    });
    renderAt("/policies/nightly/versions/3");
    const snapshots = await screen.findByRole("region", { name: "Expire snapshots" });
    const unset = within(snapshots).getByText((_, element) => element?.tagName === "DD" && element.textContent === "The table's history.expire.* / Iceberg default");
    expect(within(unset).getByText("history.expire.*")).toHaveClass("font-mono");
    expect(within(snapshots).getByText("Expire snapshots older than 7 d")).toBeInTheDocument();
  });

  it("sets an identifier option in mono and a formatted size as plain text", async () => {
    const content = policyContentFixture();
    stubCatalogApi({
      "GET /v1/maintenance-policies/nightly/versions/4": () =>
        jsonResponse({
          ...content,
          name: "nightly",
          version: 4,
          created_at: "2026-11-05T09:00:00Z",
          rewrite_data_files: {
            target: { reducible_files: { at_most: 5 }, per: "partition" },
            options: { strategy: "sort", sort_order: "id DESC", max_file_group_size_bytes: 1073741824 },
          },
        }),
    });
    renderAt("/policies/nightly/versions/4");
    const data = await screen.findByRole("region", { name: "Rewrite data files" });
    expect(within(data).getByText("id DESC")).toHaveClass("font-mono");
    const size = within(data).getByText("Max file group size: 1.0 GB");
    expect(size.tagName).toBe("LI");
    expect(size.querySelector(".font-mono")).toBeNull();
  });

  it("says when the version does not exist", async () => {
    stubCatalogApi({
      "GET /v1/maintenance-policies/nightly/versions/9": () => jsonResponse({ detail: "version 9 of nightly not found" }, 404),
    });
    renderAt("/policies/nightly/versions/9");
    expect(await screen.findByText("Could not load nightly v9: version 9 of nightly not found")).toBeInTheDocument();
  });
});
