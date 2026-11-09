import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useNavigate } from "react-router";
import { beforeEach, describe, expect, it } from "vitest";
import type { TableMaintenanceRunApiResponse } from "../../api/generated/model";
import { stubCatalogApi, type StubbedCall } from "../../test/catalogApiStub";
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

const OLDER_RUN: TableMaintenanceRunApiResponse = {
  ...RUN,
  run_id: "run-2",
  execution_ref: "table-maintenance:table=uuid-orders:run=run-2",
  trigger: "scheduled",
  status: "succeeded",
  operations: [],
};

function GoTo({ to }: { to: string }) {
  const navigate = useNavigate();
  return (
    <button type="button" onClick={() => navigate(to)}>
      go
    </button>
  );
}

function renderTab(route = "/", extra: React.ReactNode = null) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>
        <MaintenanceTab tableUuid="uuid-orders" />
        {extra}
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("MaintenanceTab", () => {
  let calls: StubbedCall[];

  beforeEach(() => {
    calls = stubCatalogApi({
      "GET /v1/tables/uuid-orders/table-maintenance-runs": () => jsonResponse([RUN]),
    });
  });

  it("lists runs with trigger, status and duration", async () => {
    renderTab();
    expect(await screen.findByText("manual")).toBeInTheDocument();
    expect(screen.getByText("Failed")).toHaveClass("bg-negative-container");
    expect(screen.getByText("2m 30s")).toBeInTheDocument();
    expect(calls[0]?.path).toBe("/v1/tables/uuid-orders/table-maintenance-runs");
  });

  it("shows per-operation attempts, metrics and error when expanded", async () => {
    const user = userEvent.setup();
    renderTab();
    await user.click(await screen.findByText("manual"));
    expect(screen.getByText("table-maintenance:table=uuid-orders:run=run-1")).toBeInTheDocument();
    expect(screen.getByText("rewrite_data_files")).toBeInTheDocument();
    expect(screen.getByText("1 attempt")).toBeInTheDocument();
    expect(screen.getByText("rewritten_data_files_count: 12")).toBeInTheDocument();
    expect(screen.getByText("3 attempts")).toBeInTheDocument();
    expect(screen.getByText("snapshot store unreachable")).toBeInTheDocument();
  });

  it("expands and collapses a run from the keyboard", async () => {
    const user = userEvent.setup();
    renderTab();
    await screen.findByText("manual");
    await user.tab();
    await user.tab();
    const toggle = screen.getByRole("button", { name: "Expand run run-1" });
    expect(toggle).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("snapshot store unreachable")).toBeInTheDocument();
    await user.keyboard("{Enter}");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("snapshot store unreachable")).not.toBeInTheDocument();
  });

  it("maintenance tab opens the run named in the url", async () => {
    calls = stubCatalogApi({
      "GET /v1/tables/uuid-orders/table-maintenance-runs": () => jsonResponse([RUN, OLDER_RUN]),
    });
    renderTab("/?run=run-2");
    const opened = await screen.findByRole("button", { name: "Collapse run run-2" });
    expect(opened).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("table-maintenance:table=uuid-orders:run=run-2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Expand run run-1" })).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("This run is no longer available")).not.toBeInTheDocument();
  });

  it("unknown run id shows the missing-run banner and the list", async () => {
    renderTab("/?run=run-gone");
    expect(screen.queryByText("This run is no longer available")).not.toBeInTheDocument();
    expect(await screen.findByText("This run is no longer available")).toBeInTheDocument();
    expect(screen.getByText("manual")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Expand run run-1" })).toHaveAttribute("aria-expanded", "false");
  });

  it("changing ?run= while the tab is mounted opens the new run", async () => {
    const user = userEvent.setup();
    calls = stubCatalogApi({
      "GET /v1/tables/uuid-orders/table-maintenance-runs": () => jsonResponse([RUN, OLDER_RUN]),
    });
    renderTab("/?run=run-gone", <GoTo to="/?run=run-2" />);
    expect(await screen.findByText("This run is no longer available")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "go" }));
    expect(await screen.findByRole("button", { name: "Collapse run run-2" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(screen.queryByText("This run is no longer available")).not.toBeInTheDocument();
  });
});
