import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useNavigate } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { TableMaintenanceRunApiResponse, TableMaintenanceRunAttemptApiResponse } from "../../api/generated/model";
import { stubCatalogApi, type StubbedCall } from "../../test/catalogApiStub";
import { jsonResponse } from "../../test/fixtures";
import { MaintenanceTab } from "./MaintenanceTab";

const RUN: TableMaintenanceRunApiResponse = {
  run_id: "run-1",
  table_uuid: "uuid-orders",
  execution_ref: "table-maintenance:table-uuid=uuid-orders",
  trigger: "manual",
  priority: "P3",
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
      filters: [],
      attempt_history: [
        {
          attempt: 1,
          size: "S",
          status: "succeeded",
          started_at: "2026-10-31T10:00:00Z",
          started_running_at: "2026-10-31T10:00:00Z",
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
      filters: [],
      attempt_history: [1, 2, 3].map((attempt) => ({
        attempt,
        size: "S",
        status: "failed",
        started_at: "2026-10-31T10:01:00Z",
        started_running_at: "2026-10-31T10:01:00Z",
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
  execution_ref: "table-maintenance:table-uuid=uuid-orders",
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
      filters: [],
      attempt_history: [
        {
          attempt: 1,
          size: "S",
          status: "failed",
          started_at: "2026-10-31T10:00:00Z",
          started_running_at: "2026-10-31T10:00:20Z",
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
          started_running_at: "2026-10-31T10:03:05Z",
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

const SCOPED_RUN: TableMaintenanceRunApiResponse = {
  ...ESCALATED_RUN,
  run_id: "run-5",
  trigger: "scheduled",
  operations: [
    {
      ...ESCALATED_RUN.operations[0]!,
      filters: [
        { spec_id: 0, where: "(`region` = 'eu')" },
        { spec_id: 1, where: "(`region` = 'us')" },
      ],
    },
    { ...RUN.operations[1]!, status: "succeeded", attempts: 1, error: null, attempt_history: [] },
  ],
};

const LEGACY_RUN: TableMaintenanceRunApiResponse = {
  ...RUN,
  run_id: "run-4",
  execution_ref: "table-maintenance:table-uuid=uuid-orders",
  trigger: "event",
  operations: [{ ...RUN.operations[1]!, attempts: 2, error: "spark job failed", attempt_history: [] }],
};

const OLDER_RUN: TableMaintenanceRunApiResponse = {
  ...RUN,
  run_id: "run-2",
  execution_ref: "table-maintenance:table-uuid=uuid-orders",
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

  it("shows the load error when the first read fails", async () => {
    calls = stubCatalogApi({
      "GET /v1/tables/uuid-orders/table-maintenance-runs": () => jsonResponse({ detail: "runs unavailable" }, 500),
    });
    renderTab();
    expect(await screen.findByText("Could not load maintenance runs: runs unavailable")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("shows per-operation attempts, metrics and error when expanded", async () => {
    const user = userEvent.setup();
    renderTab();
    await user.click(await screen.findByText("manual"));
    expect(screen.getByText("table-maintenance:table-uuid=uuid-orders")).toBeInTheDocument();
    expect(screen.getByText("rewrite_data_files")).toBeInTheDocument();
    expect(screen.getByText("1 attempt")).toBeInTheDocument();
    expect(screen.getByText("rewritten_data_files_count: 12")).toBeInTheDocument();
    expect(screen.getByText("3 attempts")).toBeInTheDocument();
    expect(screen.getByText("snapshot store unreachable")).toBeInTheDocument();
  });

  it("says which partitions a compaction passed to rewrite_data_files", async () => {
    stubCatalogApi({
      "GET /v1/tables/uuid-orders/table-maintenance-runs": () => jsonResponse([SCOPED_RUN]),
    });
    const user = userEvent.setup();
    renderTab();
    await user.click(await screen.findByText("scheduled"));
    expect(screen.getByText("Scope: Partitions over the target")).toBeInTheDocument();
    expect(screen.getByText("spec 0: (`region` = 'eu')")).toBeInTheDocument();
    expect(screen.getByText("spec 1: (`region` = 'us')")).toBeInTheDocument();
  });

  it("says a manual compaction covers the whole table", async () => {
    const user = userEvent.setup();
    renderTab();
    await user.click(await screen.findByText("manual"));
    expect(screen.getByText("Scope: Whole table")).toBeInTheDocument();
    expect(screen.queryByText(/^spec \d+:/)).not.toBeInTheDocument();
  });

  it("shows no scope for an operation other than a compaction", async () => {
    stubCatalogApi({
      "GET /v1/tables/uuid-orders/table-maintenance-runs": () =>
        jsonResponse([{ ...RUN, operations: [RUN.operations[1]!] }]),
    });
    const user = userEvent.setup();
    renderTab();
    await user.click(await screen.findByText("manual"));
    expect(screen.getByText("expire_snapshots")).toBeInTheDocument();
    expect(screen.queryByText(/^Scope:/)).not.toBeInTheDocument();
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
      ["1", "S", "Failed", "20s", "1m 40s", "Out of memory", "Did not finish", "Retrying at size M"],
      ["2", "M", "Succeeded", "5s", "5m 55s", "", "Finished", "Done"],
    ]);
    expect(within(rows[0]!).getByText("Failed")).toHaveClass("bg-negative-container");
    expect(within(attempts).getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
      "Attempt",
      "Size",
      "Result",
      "Queued",
      "Ran",
      "Reason",
      "Event log",
      "Next",
    ]);
  });

  describe("with a run in flight", () => {
    const NOW = new Date("2026-11-20T10:10:00Z");

    function attemptOf(overrides: Partial<TableMaintenanceRunAttemptApiResponse>) {
      return {
        ...ESCALATED_RUN.operations[0]!.attempt_history[0]!,
        failure_class: null,
        error: null,
        event_log_finished: null,
        next_step: null,
        next_size: null,
        finished_at: null,
        ...overrides,
      };
    }

    const IN_FLIGHT: TableMaintenanceRunApiResponse = {
      ...ESCALATED_RUN,
      status: "running",
      finished_at: null,
      operations: [
        {
          ...ESCALATED_RUN.operations[0]!,
          status: "running",
          attempt_history: [
            attemptOf({
              attempt: 1,
              status: "failed",
              started_at: "2026-11-19T10:00:00Z",
              started_running_at: null,
              finished_at: "2026-11-20T10:00:00Z",
              failure_class: "queue_timeout",
              next_step: "not_retried",
            }),
            attemptOf({
              attempt: 2,
              status: "running",
              started_at: "2026-11-20T09:55:00Z",
              started_running_at: "2026-11-20T10:03:00Z",
            }),
            attemptOf({ attempt: 3, status: "queued", started_at: "2026-11-20T10:05:00Z", started_running_at: null }),
          ],
        },
      ],
    };

    const RUNS_PATH = "/v1/tables/uuid-orders/table-maintenance-runs";
    const runReads = () => calls.filter((call) => call.method === "GET" && call.path === RUNS_PATH).length;

    afterEach(() => {
      vi.useRealTimers();
    });

    it("shows a queued attempt waiting, a running one counting and a queue timeout never running", async () => {
      vi.useFakeTimers({ now: NOW, toFake: ["Date"] });
      calls = stubCatalogApi({ [`GET ${RUNS_PATH}`]: () => jsonResponse([IN_FLIGHT]) });
      const user = userEvent.setup();
      renderTab();
      await user.click(await screen.findByText("scheduled"));
      const attempts = screen.getByRole("table", { name: "Attempts of rewrite_data_files" });
      const rows = within(attempts)
        .getAllByRole("row")
        .slice(1)
        .map((row) => within(row).getAllByRole("cell").map((cell) => cell.textContent));
      expect(rows.map((cells) => cells.slice(2, 6))).toEqual([
        ["Failed", "24h 0m", "—", "Waited too long in the queue"],
        ["Running", "8m 0s", "7m 0s (running)", ""],
        ["Queued", "5m 0s (waiting)", "—", ""],
      ]);
      expect(within(attempts).getByText("Queued", { selector: "span" })).toHaveClass("bg-surface-container-dim");
    });

    it("reads the runs again while one is in flight, so the counters move", async () => {
      vi.useFakeTimers({ toFake: ["setTimeout", "setInterval", "clearTimeout", "clearInterval", "Date"], shouldAdvanceTime: true });
      calls = stubCatalogApi({ [`GET ${RUNS_PATH}`]: () => jsonResponse([IN_FLIGHT]) });
      renderTab();
      await screen.findByText("scheduled");
      expect(runReads()).toBe(1);
      await vi.advanceTimersByTimeAsync(15_500);
      await vi.waitFor(() => expect(runReads()).toBeGreaterThanOrEqual(2));
    });

    describe("while the runs are read again in the background", () => {
      const REFRESH_FAILED = "Could not refresh. Times shown are from the last read.";
      const FAKE_TIMERS: Parameters<typeof vi.useFakeTimers>[0] = {
        toFake: ["setTimeout", "setInterval", "clearTimeout", "clearInterval", "Date"],
        shouldAdvanceTime: true,
      };

      // Answers each read with the next of `answers`, then repeats the last.
      function readsAnswering(...answers: (() => Response)[]) {
        let read = 0;
        calls = stubCatalogApi({
          [`GET ${RUNS_PATH}`]: () => answers[Math.min(read++, answers.length - 1)]!(),
        });
      }
      const ok = () => jsonResponse([IN_FLIGHT]);
      const failing = () => jsonResponse({ detail: "runs unavailable" }, 500);

      async function expandRun() {
        const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) });
        renderTab();
        await user.click(await screen.findByText("scheduled"));
        expect(screen.getByRole("button", { name: "Collapse run run-3" })).toHaveAttribute("aria-expanded", "true");
      }

      it("keeps an expanded run expanded across a refetch that succeeds", async () => {
        vi.useFakeTimers(FAKE_TIMERS);
        readsAnswering(ok, ok);
        await expandRun();
        await vi.advanceTimersByTimeAsync(15_500);
        await vi.waitFor(() => expect(runReads()).toBeGreaterThanOrEqual(2));
        expect(screen.getByRole("button", { name: "Collapse run run-3" })).toHaveAttribute("aria-expanded", "true");
        expect(screen.getByRole("table", { name: "Attempts of rewrite_data_files" })).toBeInTheDocument();
        expect(screen.queryByText(REFRESH_FAILED)).not.toBeInTheDocument();
      });

      it("keeps the table and the expanded run when a refetch fails, and drops the note once one succeeds", async () => {
        vi.useFakeTimers(FAKE_TIMERS);
        readsAnswering(ok, failing, ok);
        await expandRun();
        await vi.advanceTimersByTimeAsync(15_500);
        expect(await screen.findByText(REFRESH_FAILED)).toBeInTheDocument();
        expect(screen.queryByText(/^Could not load maintenance runs/)).not.toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Collapse run run-3" })).toHaveAttribute("aria-expanded", "true");
        expect(screen.getByRole("table", { name: "Attempts of rewrite_data_files" })).toBeInTheDocument();
        await vi.advanceTimersByTimeAsync(15_500);
        await vi.waitFor(() => expect(screen.queryByText(REFRESH_FAILED)).not.toBeInTheDocument());
        expect(screen.getByRole("button", { name: "Collapse run run-3" })).toHaveAttribute("aria-expanded", "true");
      });
    });

    it("does not read the runs again when every one has ended", async () => {
      vi.useFakeTimers({ toFake: ["setTimeout", "setInterval", "clearTimeout", "clearInterval", "Date"], shouldAdvanceTime: true });
      calls = stubCatalogApi({ [`GET ${RUNS_PATH}`]: () => jsonResponse([ESCALATED_RUN]) });
      renderTab();
      await screen.findByText("scheduled");
      await vi.advanceTimersByTimeAsync(60_000);
      expect(runReads()).toBe(1);
    });
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
    expect(screen.getByText("table-maintenance:table-uuid=uuid-orders")).toBeInTheDocument();
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
