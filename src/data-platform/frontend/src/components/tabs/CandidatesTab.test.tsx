import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import type {
  CompactionCandidateApiResponse,
  CompactionCandidatesApiResponse,
} from "../../api/generated/model";
import { formatTimestamp } from "../../format";
import { stubCatalogApi } from "../../test/catalogApiStub";
import { jsonResponse, SCHEDULER_SETTINGS } from "../../test/fixtures";
import { CandidatesTab } from "./CandidatesTab";

const PATH = "GET /v1/tables/uuid-orders/compaction-candidates";
const SETTINGS = "GET /v1/scheduler-settings";

const THREE_HOURS_AGO = new Date(Date.now() - (3 * 3600 + 60) * 1000).toISOString();

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
    priority: "P2",
    granted_round_id: null,
    granted_round_started_at: null,
    pending_since: null,
    overdue: false,
    ...overrides,
  };
}

const LIST: CompactionCandidatesApiResponse = {
  partitions_per_run: 1,
  candidates: [
    candidate("2026-11-04", { state: "claimed", claimed_by_run_id: "run-7", score: 0.91, reducible_files: 1250 }),
    candidate("2026-11-03", { state: "held", hold_reason: "recently_written", score: 0.8 }),
    candidate("2026-11-02", {
      rank: 1,
      score: 0.6,
      data_bytes: 3 * 1024 * 1024,
      priority: "P0",
      pending_since: THREE_HOURS_AGO,
      overdue: true,
    }),
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
    stubCatalogApi({ [PATH]: () => jsonResponse(LIST), [SETTINGS]: () => jsonResponse(SCHEDULER_SETTINGS) });
    renderTab();
    const table = await screen.findByRole("table", { name: "Compaction candidates, best first" });
    await within(table).findByText("P0 (within 1 h)");
    expect(within(table).getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
      "Partition",
      "Priority",
      "Score",
      "Removable files",
      "Data",
      "Est. GB·h",
      "State",
      "Why not picked",
    ]);
    expect(rowsOf(table)).toEqual([
      ["day=2026-11-04", "P2 (within 8 h)", "0.91", "1,250", "4.0 KB", "0.25", "Claimed", "In run run-7"],
      [
        "day=2026-11-03",
        "P2 (within 8 h)",
        "0.80",
        "12",
        "4.0 KB",
        "0.25",
        "Held",
        "Still being written; checked again after a quiet period",
      ],
      [
        "day=2026-11-02",
        "P0 (within 1 h)",
        "0.60",
        "12",
        "3.0 MB",
        "0.25",
        "PendingOverdueWaited 3 h; P0 allows 1 h",
        "Waiting for the next round",
      ],
      [
        "day=2026-11-01",
        "P2 (within 8 h)",
        "0.40",
        "12",
        "4.0 KB",
        "1.50",
        "Pending",
        "Waiting for a later round: below the top 1 (1 per run)",
      ],
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
    expect(rowsOf(table).map((row) => row[5])).toEqual(["< 0.01", "0.00"]);
  });

  it("keeps held and pending candidates neutral", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse(LIST) });
    renderTab();
    const table = await screen.findByRole("table", { name: "Compaction candidates, best first" });
    expect(within(table).getByText("Held")).toHaveClass("bg-surface-container-dim");
    expect(within(table).getAllByText("Pending")[0]).toHaveClass("bg-surface-container-dim");
  });

  it("marks an overdue candidate with a notice, the only colour on the tab", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse(LIST) });
    renderTab();
    const table = await screen.findByRole("table", { name: "Compaction candidates, best first" });
    expect(within(table).getAllByText("Overdue")).toHaveLength(1);
    expect(within(table).getByText("Overdue")).toHaveClass("bg-notice-container");
  });

  it("says why a candidate is overdue even before the scheduler settings load", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse(LIST) });
    renderTab();
    expect(await screen.findByText("Waited 3 h, longer than P0 allows")).toBeInTheDocument();
  });

  it("names the round that granted a candidate by its start time and links to it", async () => {
    const list: CompactionCandidatesApiResponse = {
      partitions_per_run: 10,
      candidates: [
        candidate("2026-11-02", {
          state: "granted",
          granted_round_id: "compaction-rounds-2026-11-13T12:00:00Z",
          granted_round_started_at: "2026-11-13T12:00:03Z",
        }),
      ],
    };
    stubCatalogApi({ [PATH]: () => jsonResponse(list) });
    renderTab();
    const table = await screen.findByRole("table", { name: "Compaction candidates, best first" });
    const started = formatTimestamp("2026-11-13T12:00:03Z");
    expect(rowsOf(table)[0]!.slice(-2)).toEqual(["Granted", `Granted in round ${started}`]);
    expect(within(table).getByRole("link", { name: started })).toHaveAttribute(
      "href",
      "/compaction-rounds?round=compaction-rounds-2026-11-13T12%3A00%3A00Z",
    );
  });

  it("says how many partitions a run takes", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse(LIST) });
    renderTab();
    expect(
      await screen.findByText(
        "Each compaction round grants the best pending partitions across all tables while its budget lasts, at most 1 per table.",
        { exact: false },
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "See the compaction rounds" })).toHaveAttribute("href", "/compaction-rounds");
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
