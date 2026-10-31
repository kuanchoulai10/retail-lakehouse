import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TableMaintenanceRunApiResponse } from "../../api/types";
import { jsonResponse } from "../../test/fixtures";
import { MaintenanceTab } from "./MaintenanceTab";

const RUN: TableMaintenanceRunApiResponse = {
  run_id: "run-1",
  table_uuid: "uuid-orders",
  execution_ref: "table-maintenance:table=uuid-orders:run=run-1",
  trigger: "manual",
  status: "failed",
  created_at: "2026-10-31T10:00:00Z",
  finished_at: "2026-10-31T10:02:30Z",
  operations: [
    {
      operation: "rewrite_data_files",
      status: "succeeded",
      attempts: 1,
      started_at: "2026-10-31T10:00:00Z",
      finished_at: "2026-10-31T10:01:00Z",
      job_name: "job-a",
      metrics: { rewritten_data_files_count: 12 },
      error: null,
      expected_files: null,
    },
    {
      operation: "expire_snapshots",
      status: "failed",
      attempts: 3,
      started_at: "2026-10-31T10:01:00Z",
      finished_at: "2026-10-31T10:02:30Z",
      job_name: "job-b",
      metrics: {},
      error: "snapshot store unreachable",
      expected_files: null,
    },
  ],
};

describe("MaintenanceTab", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse([RUN])));
  });

  it("lists runs with trigger, status and duration", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <MaintenanceTab tableUuid="uuid-orders" />
      </QueryClientProvider>,
    );
    expect(await screen.findByText("manual")).toBeInTheDocument();
    expect(screen.getByText("FAILED")).toBeInTheDocument();
    expect(screen.getByText("2m 30s")).toBeInTheDocument();
    expect(vi.mocked(fetch).mock.calls[0]?.[0]).toBe(
      "/console/api/v1/tables/uuid-orders/table-maintenance-runs",
    );
  });

  it("shows per-operation attempts, metrics and error when expanded", async () => {
    const user = userEvent.setup();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <MaintenanceTab tableUuid="uuid-orders" />
      </QueryClientProvider>,
    );
    await user.click(await screen.findByText("manual"));
    expect(screen.getByText("table-maintenance:table=uuid-orders:run=run-1")).toBeInTheDocument();
    expect(screen.getByText("rewrite_data_files")).toBeInTheDocument();
    expect(screen.getByText("1 attempt")).toBeInTheDocument();
    expect(screen.getByText("rewritten_data_files_count: 12")).toBeInTheDocument();
    expect(screen.getByText("3 attempts")).toBeInTheDocument();
    expect(screen.getByText("snapshot store unreachable")).toBeInTheDocument();
  });
});
