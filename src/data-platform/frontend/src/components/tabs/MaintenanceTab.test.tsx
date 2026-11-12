import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
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
      attempt_history: [
        {
          attempt: 1,
          size: "S",
          status: "succeeded",
          started_at: "2026-10-31T10:00:00Z",
          finished_at: "2026-10-31T10:01:00Z",
          failure_class: null,
          error: null,
          event_log_finished: true,
          next_step: "done",
          next_size: null,
        },
      ],
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
      attempt_history: [1, 2, 3].map((attempt) => ({
        attempt,
        size: "S",
        status: "failed",
        started_at: "2026-10-31T10:01:00Z",
        finished_at: "2026-10-31T10:02:30Z",
        failure_class: "other",
        error: "snapshot store unreachable",
        event_log_finished: true,
        next_step: attempt === 3 ? "attempts_used" : "retry_same",
        next_size: attempt === 3 ? null : "S",
      })),
    },
  ],
};

const ESCALATED_RUN: TableMaintenanceRunApiResponse = {
  ...RUN,
  run_id: "run-3",
  execution_ref: "table-maintenance:table=uuid-orders:run=run-3",
  trigger: "scheduled",
  status: "succeeded",
  operations: [
    {
      operation: "rewrite_data_files",
      status: "succeeded",
      attempts: 2,
      started_at: "2026-10-31T10:03:00Z",
      finished_at: "2026-10-31T10:09:00Z",
      job_name: "job-c",
      metrics: { rewritten_data_files_count: 24 },
      error: null,
      expected_files: null,
      attempt_history: [
        {
          attempt: 1,
          size: "S",
          status: "failed",
          started_at: "2026-10-31T10:00:00Z",
          finished_at: "2026-10-31T10:02:00Z",
          failure_class: "oom",
          error: "java.lang.OutOfMemoryError: Java heap space",
          event_log_finished: false,
          next_step: "retry_larger",
          next_size: "M",
        },
        {
          attempt: 2,
          size: "M",
          status: "succeeded",
          started_at: "2026-10-31T10:03:00Z",
          finished_at: "2026-10-31T10:09:00Z",
          failure_class: null,
          error: null,
          event_log_finished: true,
          next_step: "done",
          next_size: null,
        },
      ],
    },
  ],
};

const LEGACY_RUN: TableMaintenanceRunApiResponse = {
  ...RUN,
  run_id: "run-4",
  execution_ref: "table-maintenance:table=uuid-orders:run=run-4",
  trigger: "event",
  operations: [{ ...RUN.operations[1]!, attempts: 2, error: "spark job failed", attempt_history: [] }],
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

  it("lists every attempt with size, result, reason, event log and next step", async () => {
    stubCatalogApi({
      "GET /v1/tables/uuid-orders/table-maintenance-runs": () => jsonResponse([ESCALATED_RUN]),
    });
    const user = userEvent.setup();
    renderTab();
    await user.click(await screen.findByText("scheduled"));
    const attempts = screen.getByRole("table", { name: "Attempts of rewrite_data_files" });
    const rows = within(attempts).getAllByRole("row").slice(1);
    expect(rows.map((row) => within(row).getAllByRole("cell").map((cell) => cell.textContent))).toEqual([
      ["1", "S", "Failed", "Out of memory", "Did not finish", "Retrying at size M"],
      ["2", "M", "Succeeded", "", "Finished", "Done"],
    ]);
    expect(within(rows[0]!).getByText("Failed")).toHaveClass("bg-negative-container");
    expect(within(attempts).getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
      "Attempt",
      "Size",
      "Result",
      "Reason",
      "Event log",
      "Next",
    ]);
  });

  it("keeps the attempt count for runs from before attempt history", async () => {
    stubCatalogApi({
      "GET /v1/tables/uuid-orders/table-maintenance-runs": () => jsonResponse([LEGACY_RUN]),
    });
    const user = userEvent.setup();
    renderTab();
    await user.click(await screen.findByText("event"));
    expect(screen.getByText("2 attempts")).toBeInTheDocument();
    expect(screen.getByText("spark job failed")).toHaveClass("text-negative-text");
    expect(screen.queryByRole("table", { name: /^Attempts of/ })).not.toBeInTheDocument();
  });

  it("expands and collapses a run from the keyboard", async () => {
    const user = userEvent.setup();
    renderTab();
    await screen.findByText("manual");
    await user.tab();
    expect(screen.getByRole("link", { name: "Running workflows in Temporal" })).toHaveFocus();
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
