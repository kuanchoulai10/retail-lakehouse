import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import type { CompactionCandidateApiResponse, CompactionCandidatesApiResponse } from "../../api/generated/model";
import { stubCatalogApi } from "../../test/catalogApiStub";
import { jsonResponse } from "../../test/fixtures";
import { CandidatesTab } from "./CandidatesTab";

const PATH = "GET /v1/tables/uuid-orders/compaction-candidates";

function candidate(day: string, overrides: Partial<CompactionCandidateApiResponse>): CompactionCandidateApiResponse {
  return {
    partition: { spec_id: 0, values: [day] },
    partition_label: `day=${day}`,
    state: "pending",
    hold_reason: null,
    reducible_files: 12,
    data_bytes: 4096,
    estimated_gb_hours: 0.25,
    score: 0.5,
    rank: null,
    claimed_by_run_id: null,
    lease_expires_at: null,
    last_written_at: null,
    observed_at: "2026-11-13T09:00:00Z",
    ...overrides,
  };
}

const LIST: CompactionCandidatesApiResponse = {
  partitions_per_run: 1,
  candidates: [
    candidate("2026-11-04", { state: "claimed", claimed_by_run_id: "run-7", score: 0.91, reducible_files: 1250 }),
    candidate("2026-11-03", { state: "held", hold_reason: "recently_written", score: 0.8 }),
    candidate("2026-11-02", { rank: 1, score: 0.6, data_bytes: 3 * 1024 * 1024 }),
    candidate("2026-11-01", { rank: 2, score: 0.4, estimated_gb_hours: 1.5 }),
  ],
};

function renderTab() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <CandidatesTab tableUuid="uuid-orders" />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function rowsOf(table: HTMLElement): string[][] {
  return within(table)
    .getAllByRole("row")
    .slice(1)
    .map((row) => within(row).getAllByRole("cell").map((cell) => cell.textContent ?? ""));
}

describe("CandidatesTab", () => {
  it("lists every candidate with its worth, state and why it was not picked", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse(LIST) });
    renderTab();
    const table = await screen.findByRole("table", { name: "Compaction candidates, best first" });
    expect(within(table).getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
      "Partition",
      "Score",
      "Removable files",
      "Data",
      "Est. GB·h",
      "State",
      "Why not picked",
    ]);
    expect(rowsOf(table)).toEqual([
      ["day=2026-11-04", "0.91", "1,250", "4.0 KB", "0.25", "Claimed", "In run run-7"],
      ["day=2026-11-03", "0.80", "12", "4.0 KB", "0.25", "Held", "Still being written; checked again after a quiet period"],
      ["day=2026-11-02", "0.60", "12", "3.0 MB", "0.25", "Pending", ""],
      ["day=2026-11-01", "0.40", "12", "4.0 KB", "1.50", "Pending", "Score below the top 1 (1 per run)"],
    ]);
  });

  it("shows a cost too small to round as below one hundredth, and none as zero", async () => {
    const list: CompactionCandidatesApiResponse = {
      partitions_per_run: 10,
      candidates: [
        candidate("2026-11-02", { rank: 1, estimated_gb_hours: 0.0000023 }),
        candidate("2026-11-01", { rank: 2, estimated_gb_hours: 0 }),
      ],
    };
    stubCatalogApi({ [PATH]: () => jsonResponse(list) });
    renderTab();
    const table = await screen.findByRole("table", { name: "Compaction candidates, best first" });
    expect(rowsOf(table).map((row) => row[4])).toEqual(["< 0.01", "0.00"]);
  });

  it("keeps held and pending candidates neutral", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse(LIST) });
    renderTab();
    const table = await screen.findByRole("table", { name: "Compaction candidates, best first" });
    expect(within(table).getByText("Held")).toHaveClass("bg-surface-container-dim");
    expect(within(table).getAllByText("Pending")[0]).toHaveClass("bg-surface-container-dim");
  });

  it("says how many partitions a run takes", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse(LIST) });
    renderTab();
    expect(await screen.findByText("Each scheduled run compacts the top 1 pending partition.")).toBeInTheDocument();
  });

  it("says when no partition needs compaction", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse({ partitions_per_run: 10, candidates: [] }) });
    renderTab();
    expect(await screen.findByText("No partition needs compaction.")).toBeInTheDocument();
  });

  it("shows the error when the list cannot load", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse({ detail: "database down" }, 500) });
    renderTab();
    expect(await screen.findByText(/^Could not load compaction candidates/)).toBeInTheDocument();
  });
});
