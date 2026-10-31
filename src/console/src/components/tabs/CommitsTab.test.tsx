import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TableCommitApiResponse } from "../../api/types";
import { jsonResponse } from "../../test/fixtures";
import { CommitsTab } from "./CommitsTab";

function commit(overrides: Partial<TableCommitApiResponse>): TableCommitApiResponse {
  return {
    snapshot_id: 1,
    parent_id: null,
    committed_at: "2026-10-31T10:00:00Z",
    operation: "append",
    writer: "kafka_connect",
    added_records: 10,
    deleted_records: 0,
    added_data_files: 2,
    deleted_data_files: 0,
    added_delete_files: 0,
    removed_delete_files: 0,
    summary: { "kafka.connect.task-id": "0" },
    ...overrides,
  };
}

const ITEMS = [
  commit({ snapshot_id: 100, parent_id: 99, committed_at: "2026-10-31T10:00:00Z" }),
  commit({
    snapshot_id: 200,
    parent_id: 100,
    committed_at: "2026-10-31T11:00:00Z",
    operation: "replace",
    writer: "spark",
    added_records: null,
    deleted_records: null,
    summary: { "spark.app.id": "app-1" },
  }),
];

function renderTab() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <CommitsTab tableUuid="uuid-orders" />
    </QueryClientProvider>,
  );
}

describe("CommitsTab", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ items: ITEMS, truncated: false })),
    );
  });

  it("lists commits newest first with writer labels", async () => {
    renderTab();
    await screen.findByText("Kafka Connect");
    const rows = screen.getAllByTestId("commit-row");
    expect(rows).toHaveLength(2);
    expect(within(rows[0] as HTMLElement).getByText("replace")).toBeInTheDocument();
    expect(within(rows[0] as HTMLElement).getByText("Spark")).toBeInTheDocument();
    expect(within(rows[1] as HTMLElement).getByText("Kafka Connect")).toBeInTheDocument();
    expect(vi.mocked(fetch).mock.calls[0]?.[0]).toBe("/console/api/v1/tables/uuid-orders/commits");
  });

  it("renders null counters as a dash", async () => {
    renderTab();
    await screen.findByText("Spark");
    const row = screen.getAllByTestId("commit-row")[0] as HTMLElement;
    expect(within(row).getAllByText("—").length).toBeGreaterThanOrEqual(2);
  });

  it("expands a row to show the snapshot id and summary JSON", async () => {
    const user = userEvent.setup();
    renderTab();
    await screen.findByText("Spark");
    await user.click(screen.getAllByTestId("commit-row")[1] as HTMLElement);
    expect(screen.getByText("Snapshot id: 100")).toBeInTheDocument();
    expect(screen.getByText("Parent id: 99")).toBeInTheDocument();
    expect(screen.getByText(/"kafka.connect.task-id": "0"/)).toBeInTheDocument();
  });
});
