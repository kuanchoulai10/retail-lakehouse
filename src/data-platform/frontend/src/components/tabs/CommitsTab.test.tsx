import { TooltipProvider } from "@retail-lakehouse/design-system";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import type { TableCommitApiResponse } from "../../api/generated/model";
import { stubCatalogApi, type StubbedCall } from "../../test/catalogApiStub";
import { jsonResponse } from "../../test/fixtures";
import { CommitsTab } from "./CommitsTab";

function commit(overrides: Partial<TableCommitApiResponse>): TableCommitApiResponse {
  return {
    snapshot_id: "1",
    parent_id: null,
    committed_at: "2026-10-31T12:00:00Z",
    operation: "append",
    writer: "kafka_connect",
    added_records: 1200,
    deleted_records: 0,
    added_data_files: 4,
    deleted_data_files: 0,
    added_delete_files: 0,
    removed_delete_files: 0,
    summary: { "kafka.connect.task-id": "0" },
    ...overrides,
  };
}

// Noon UTC keeps each commit on the same calendar day in any time zone from UTC-11 to UTC+11.
const ITEMS = [
  commit({
    snapshot_id: "3051729675574597004",
    parent_id: "3051729675574597003",
    committed_at: "2026-10-30T12:00:00Z",
  }),
  commit({
    snapshot_id: "8127364509182736455",
    parent_id: "3051729675574597004",
    committed_at: "2026-10-31T12:00:00Z",
    operation: "replace",
    writer: "spark",
    added_records: null,
    deleted_records: null,
    added_data_files: 1,
    deleted_data_files: 6,
    summary: { "spark.app.id": "app-1" },
  }),
  commit({
    snapshot_id: "5964018273645190826",
    parent_id: "8127364509182736455",
    committed_at: "2026-10-31T13:00:00Z",
    operation: "delete",
    added_records: 0,
    deleted_records: 30,
    added_data_files: 0,
    deleted_data_files: 0,
  }),
];

function renderTab() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <TooltipProvider>
        <CommitsTab tableUuid="uuid-orders" />
      </TooltipProvider>
    </QueryClientProvider>,
  );
}

function day(name: string): HTMLElement {
  return screen.getByRole("region", { name });
}

function commitsOn(name: string): HTMLElement[] {
  return within(day(name)).getAllByRole("listitem");
}

describe("CommitsTab", () => {
  let calls: StubbedCall[];

  beforeEach(() => {
    calls = stubCatalogApi({
      "GET /v1/tables/uuid-orders/commits": () => jsonResponse({ items: ITEMS, truncated: false }),
    });
  });

  it("groups commits by day, newest day and newest commit first", async () => {
    renderTab();
    await screen.findByRole("region", { name: "Commits on Oct 31, 2026" });
    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual([
      "Commits on Oct 31, 2026",
      "Commits on Oct 30, 2026",
    ]);
    const latest = commitsOn("Commits on Oct 31, 2026");
    expect(latest).toHaveLength(2);
    expect(within(latest[0] as HTMLElement).getByText("5964018")).toBeInTheDocument();
    expect(within(latest[1] as HTMLElement).getByText("8127364")).toBeInTheDocument();
    expect(commitsOn("Commits on Oct 30, 2026")).toHaveLength(1);
    expect(calls[0]?.path).toBe("/v1/tables/uuid-orders/commits");
  });

  it("titles each commit with its operation and what it changed, and names the writer", async () => {
    renderTab();
    await screen.findByRole("region", { name: "Commits on Oct 30, 2026" });
    const append = commitsOn("Commits on Oct 30, 2026")[0] as HTMLElement;
    expect(within(append).getByText("Append: 1,200 rows added in 4 files")).toBeInTheDocument();
    expect(append).toHaveTextContent(/Kafka Connect committed \d+ d ago/);

    const [deletion, replace] = commitsOn("Commits on Oct 31, 2026") as [HTMLElement, HTMLElement];
    expect(within(deletion).getByText("Delete: 30 rows removed")).toBeInTheDocument();
    expect(within(replace).getByText("Replace: 1 file added, 6 files removed")).toBeInTheDocument();
    expect(replace).toHaveTextContent(/Spark committed \d+ d ago/);
  });

  it("shows the first seven digits of the snapshot id, as git shortens a commit hash", async () => {
    renderTab();
    await screen.findByRole("region", { name: "Commits on Oct 30, 2026" });
    const row = commitsOn("Commits on Oct 30, 2026")[0] as HTMLElement;
    expect(within(row).getByText("3051729")).toHaveAttribute("title", "3051729675574597004");
    expect(within(row).queryByText("3051729675574597004")).not.toBeInTheDocument();
  });

  it("shows the full ids and summary JSON when a commit's details are opened", async () => {
    const user = userEvent.setup();
    renderTab();
    await screen.findByRole("region", { name: "Commits on Oct 30, 2026" });
    const toggle = screen.getByRole("button", { name: "Details of commit 3051729675574597004" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Parent id: 3051729675574597003")).not.toBeInTheDocument();

    await user.click(toggle);

    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Snapshot id: 3051729675574597004")).toBeInTheDocument();
    expect(screen.getByText("Parent id: 3051729675574597003")).toBeInTheDocument();
    expect(screen.getByText(/"kafka.connect.task-id": "0"/)).toBeInTheDocument();
  });

  it("copies the exact 64-bit snapshot id", async () => {
    const user = userEvent.setup();
    renderTab();
    await screen.findByRole("region", { name: "Commits on Oct 30, 2026" });

    await user.click(screen.getByRole("button", { name: "Copy snapshot id 3051729675574597004" }));

    await expect(navigator.clipboard.readText()).resolves.toBe("3051729675574597004");
  });

  it("says so when the table has no commits", async () => {
    stubCatalogApi({
      "GET /v1/tables/uuid-orders/commits": () => jsonResponse({ items: [], truncated: false }),
    });
    renderTab();
    expect(await screen.findByText("No commits.")).toBeInTheDocument();
  });

  it("notes when only the newest commits are shown", async () => {
    stubCatalogApi({
      "GET /v1/tables/uuid-orders/commits": () => jsonResponse({ items: ITEMS, truncated: true }),
    });
    renderTab();
    expect(await screen.findByText("Showing the newest commits only.")).toBeInTheDocument();
  });
});
