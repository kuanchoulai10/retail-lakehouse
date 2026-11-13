import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import type { CompactionRoundApiResponse } from "../api/generated/model";
import { formatTimestamp } from "../format";
import { stubCatalogApi } from "../test/catalogApiStub";
import { jsonResponse, SCHEDULER_SETTINGS } from "../test/fixtures";
import { CompactionRoundsPage } from "./CompactionRoundsPage";

const PATH = "GET /v1/compaction-rounds?limit=50";
const SETTINGS = "GET /v1/scheduler-settings";

const ROUND: CompactionRoundApiResponse = {
  round_id: "compaction-rounds-2026-11-13T12:00:00Z",
  started_at: "2026-11-13T12:00:00Z",
  budget_gb_hours: 0.05,
  used_gb_hours: 0.04,
  picks: [
    {
      table_uuid: "u-orders",
      table_name: "iceberg.retail.orders",
      table: { catalog: "iceberg", namespace: ["retail"], name: "orders" },
      partition: { spec_id: 0, values: ["2026-11-01"] },
      partition_label: "day=2026-11-01",
      priority: "P0",
      score: 0.5,
      weighted_score: 2,
      estimated_gb_hours: 0.04,
      overdue: true,
    },
  ],
  skips: [
    {
      table_uuid: "u-gone",
      table_name: null,
      table: null,
      partition: { spec_id: -1, values: [] },
      partition_label: "whole table",
      priority: "P2",
      score: 0.6,
      weighted_score: 0.6,
      estimated_gb_hours: 0.03,
      overdue: false,
      reason: "budget_used",
    },
  ],
  skipped_total: 3,
  busy_skipped: 0,
};

const ROUND_NAME = formatTimestamp(ROUND.started_at);

function renderPage(path = "/compaction-rounds") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <CompactionRoundsPage />
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

describe("CompactionRoundsPage", () => {
  it("lists the newest rounds with their budget, use, picks and skips", async () => {
    const calls = stubCatalogApi({ [PATH]: () => jsonResponse([ROUND]) });
    renderPage();
    await screen.findByText("0.04 (80%)");
    const table = screen.getByRole("table", { name: "Compaction rounds, newest first" });
    expect(within(table).getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
      "Started",
      "Budget GB·h",
      "Used GB·h",
      "Picked",
      "Skipped",
    ]);
    expect(rowsOf(table)[0]!.slice(1)).toEqual(["0.05", "0.04 (80%)", "1", "3"]);
    expect(calls.map((c) => c.path)).toContain("/v1/compaction-rounds?limit=50");
  });

  it("opens a round, named by its start time, to what it granted and the first it skipped, with why", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse([ROUND]), [SETTINGS]: () => jsonResponse(SCHEDULER_SETTINGS) });
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: `Expand round ${ROUND_NAME}` }));

    const picks = screen.getByRole("table", { name: `Partitions round ${ROUND_NAME} granted` });
    await within(picks).findByText("P0 (within 1 h)");
    expect(rowsOf(picks)).toEqual([
      ["iceberg.retail.orders", "day=2026-11-01", "P0 (within 1 h)", "0.50", "2.00", "0.04", "Overdue"],
    ]);
    expect(within(picks).getByRole("link", { name: "iceberg.retail.orders" })).toHaveAttribute(
      "href",
      "/catalogs/iceberg/namespaces/retail/tables/orders/candidates",
    );
    const skips = screen.getByRole("table", { name: `Partitions round ${ROUND_NAME} skipped` });
    expect(rowsOf(skips)).toEqual([
      ["Dropped table u-gone", "whole table", "P2 (within 8 h)", "0.60", "0.60", "0.03", "—", "Budget used"],
    ]);
    expect(screen.getByText("The first 1 of 3 skipped partitions, in rank order.")).toBeInTheDocument();
  });

  it("keeps the workflow id as secondary detail, not as the round's name", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse([ROUND]) });
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: `Expand round ${ROUND_NAME}` }));
    expect(screen.getByText(ROUND.round_id)).toHaveClass("font-mono");
    expect(screen.getByText(ROUND.round_id).parentElement).toHaveTextContent(`Workflow id ${ROUND.round_id}`);
  });

  it("explains the weighted score, overdue and each skip reason", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse([ROUND]), [SETTINGS]: () => jsonResponse(SCHEDULER_SETTINGS) });
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: `Expand round ${ROUND_NAME}` }));
    expect(
      await screen.findByText(
        "Weighted is the score times its priority's weight (P0 × 4, P1 × 2, P2 × 1). Overdue: it waited longer than its priority allows.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Budget used: the round's GB·h budget ran out. Table's share used: the table already has as many partitions as one round gives a table. Table busy: the table is still compacting what an earlier round granted.",
      ),
    ).toBeInTheDocument();
  });

  it("counts the partitions of busy tables apart from the skips, in words", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse([{ ...ROUND, busy_skipped: 30 }]) });
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: `Expand round ${ROUND_NAME}` }));
    expect(
      screen.getByText("Left for a later round without ranking: 30 partitions of tables still busy with compaction."),
    ).toBeInTheDocument();
  });

  it("says nothing of busy tables when the round had none", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse([ROUND]) });
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: `Expand round ${ROUND_NAME}` }));
    expect(screen.queryByText(/still busy with compaction/)).not.toBeInTheDocument();
  });

  it("opens the round a link names", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse([ROUND]) });
    renderPage(`/compaction-rounds?round=${encodeURIComponent(ROUND.round_id)}`);
    expect(await screen.findByRole("table", { name: `Partitions round ${ROUND_NAME} granted` })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: `Collapse round ${ROUND_NAME}` })).toBeInTheDocument();
  });

  it("says when no round has run", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse([]) });
    renderPage();
    expect(await screen.findByText("No compaction round has run yet.")).toBeInTheDocument();
  });

  it("shows the error when the rounds cannot load", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse({ detail: "database down" }, 500) });
    renderPage();
    expect(await screen.findByText("Could not load compaction rounds: database down")).toBeInTheDocument();
  });
});
