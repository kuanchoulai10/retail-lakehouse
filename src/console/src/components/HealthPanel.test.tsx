import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { TableHealthApiResponse, TableHealthOperationApiResponse } from "../api/types";
import { HealthPanel } from "./HealthPanel";

function line(overrides: Partial<TableHealthOperationApiResponse>): TableHealthOperationApiResponse {
  return {
    operation: "rewrite_data_files",
    verdict: "due",
    measured: 12,
    threshold: 5,
    next_eligible_at: null,
    qualifying_partitions: 3,
    size_bytes: null,
    size_source: null,
    ...overrides,
  };
}

function health(overrides: Partial<TableHealthApiResponse> = {}): TableHealthApiResponse {
  return {
    scheduled: true,
    not_scheduled_reason: null,
    operations: [
      line({}),
      line({
        operation: "rewrite_manifests",
        verdict: "cooldown",
        measured: 4,
        threshold: 10,
        qualifying_partitions: null,
        next_eligible_at: "2026-11-01T09:12:00Z",
      }),
      line({ operation: "expire_snapshots", verdict: "disabled", measured: null, threshold: null }),
      line({ operation: "remove_orphan_files", verdict: "not_due", measured: null, threshold: null }),
    ],
    position_delete_files: 3,
    equality_delete_files: 1,
    ...overrides,
  };
}

function renderPanel(value: TableHealthApiResponse) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <HealthPanel tableUuid="uuid-orders" health={value} />
    </QueryClientProvider>,
  );
}

describe("HealthPanel", () => {
  it("shows the not-scheduled banner and suffixes due lines", () => {
    renderPanel(health({ scheduled: false, not_scheduled_reason: "paused" }));
    expect(screen.getByText("The scheduler skips this table: paused")).toBeInTheDocument();
    expect(
      screen.getByText(/12 reducible files in 3 partitions, threshold 5 \(would be due when resumed\)/),
    ).toBeInTheDocument();
  });

  it("shows no banner for a scheduled table", () => {
    renderPanel(health());
    expect(screen.queryByText(/The scheduler skips this table/)).not.toBeInTheDocument();
  });

  it("gives a due line a Run now button and a cooldown line none", () => {
    renderPanel(health());
    expect(screen.getAllByRole("button", { name: "Run now" })).toHaveLength(1);
    expect(screen.getByText(/in cooldown until/)).toBeInTheDocument();
    expect(screen.getByText("disabled")).toBeInTheDocument();
  });

  it("opens the run dialog with only that operation selected", async () => {
    const user = userEvent.setup();
    renderPanel(health());
    await user.click(screen.getByRole("button", { name: "Run now" }));
    expect(screen.getByRole("checkbox", { name: "rewrite_data_files" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "expire_snapshots" })).not.toBeChecked();
  });

  it("reads a not-due line without a measurement once", () => {
    renderPanel(health());
    expect(screen.getByText("not due")).toBeInTheDocument();
  });

  it("pluralises a single qualifying partition", () => {
    renderPanel(
      health({ operations: [line({ measured: 6, qualifying_partitions: 1 })] }),
    );
    expect(screen.getByText("6 reducible files in 1 partition, threshold 5")).toBeInTheDocument();
  });

  it("shows the delete file counts", () => {
    renderPanel(health());
    expect(screen.getByText("3 position, 1 equality")).toBeInTheDocument();
  });
});
