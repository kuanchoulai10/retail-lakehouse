import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import type { CompactionRoundApiResponse } from "../api/generated/model";
import { stubCatalogApi } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { CompactionRoundsPage } from "./CompactionRoundsPage";

const PATH = "GET /v1/compaction-rounds?limit=50";

const ROUND: CompactionRoundApiResponse = {
  round_id: "compaction-rounds-2026-11-13T12:00:00Z",
  started_at: "2026-11-13T12:00:00Z",
  budget_gb_hours: 0.05,
  used_gb_hours: 0.04,
  picks: [
    {
      table_uuid: "u-orders",
      table_name: "iceberg.retail.orders",
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
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
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
    await screen.findByText("0.04 of 0.05 (80%)");
    const table = screen.getByRole("table", { name: "Compaction rounds, newest first" });
    expect(within(table).getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
      "Started",
      "Used GB·h",
      "Picked",
      "Skipped",
    ]);
    expect(rowsOf(table)[0]!.slice(1)).toEqual(["0.04 of 0.05 (80%)", "1", "3"]);
    expect(calls.map((c) => c.path)).toContain("/v1/compaction-rounds?limit=50");
  });

  it("opens a round to what it granted and the first it skipped, with why", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse([ROUND]) });
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Expand round 2026-11-13T12:00:00Z" }));

    const picks = screen.getByRole("table", { name: "Partitions round 2026-11-13T12:00:00Z granted" });
    expect(rowsOf(picks)).toEqual([["iceberg.retail.orders", "day=2026-11-01", "P0", "0.50", "2.00", "0.04", "Overdue"]]);
    expect(within(picks).getByRole("link", { name: "iceberg.retail.orders" })).toHaveAttribute(
      "href",
      "/catalogs/iceberg/namespaces/retail/tables/orders/candidates",
    );
    const skips = screen.getByRole("table", { name: "Partitions round 2026-11-13T12:00:00Z skipped" });
    expect(rowsOf(skips)).toEqual([["u-gone", "whole table", "P2", "0.60", "0.60", "0.03", "—", "Budget used"]]);
    expect(screen.getByText("The first 1 of 3 skipped partitions, in rank order.")).toBeInTheDocument();
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
