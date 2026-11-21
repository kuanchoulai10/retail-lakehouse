import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { TableMaintenanceRunApiResponse, TableMaintenanceRunAttemptApiResponse } from "../../api/generated/model";
import { callsTo, stubCatalogApi, type StubbedCall } from "../../test/catalogApiStub";
import { jsonResponse } from "../../test/fixtures";
import { MaintenanceTab } from "./MaintenanceTab";

const RUNS_PATH = "/v1/tables/uuid-orders/table-maintenance-runs";
const runPath = (id: string) => `/v1/table-maintenance-runs/${id}`;

function attempt(overrides: Partial<TableMaintenanceRunAttemptApiResponse> = {}): TableMaintenanceRunAttemptApiResponse {
  return {
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
    job_name: "tm-orders-a1",
    ...overrides,
  };
}

function run(overrides: Partial<TableMaintenanceRunApiResponse>): TableMaintenanceRunApiResponse {
  return {
    run_id: "mr-1",
    table_uuid: "uuid-orders",
    execution_ref: "table-maintenance:table-uuid=uuid-orders",
    trigger: "manual",
    operation: "rewrite_data_files",
    priority: "P3",
    status: "succeeded",
    created_at: "2026-10-31T10:00:00Z",
    started_at: "2026-10-31T10:00:00Z",
    finished_at: "2026-10-31T10:01:00Z",
    filters: [],
    procedure_args: {},
    metrics: {},
    error: null,
    skip_reason: null,
    attempts: [attempt()],
    ...overrides,
  };
}

// An expiry that failed three times at S.
const EXPIRE_RUN = run({
  run_id: "mr-expire",
  operation: "expire_snapshots",
  status: "failed",
  finished_at: "2026-10-31T10:02:30Z",
  procedure_args: { older_than: "2026-10-26T10:00:00+00:00", retain_last: 5 },
  error: "snapshot store unreachable",
  attempts: [1, 2, 3].map((n) =>
    attempt({
      attempt: n,
      status: "failed",
      failure_class: "other",
      error: "snapshot store unreachable",
      next_step: n === 3 ? "attempts_used" : "retry_same",
      next_size: n === 3 ? null : "S",
      job_name: `tm-orders-expire-a${n}`,
    }),
  ),
});

// A compaction that ran out of memory at S and succeeded at M.
const ESCALATED_RUN = run({
  run_id: "mr-escalated",
  trigger: "scheduled",
  finished_at: "2026-10-31T10:09:00Z",
  priority: "P1",
  procedure_args: { options: { "target-file-size-bytes": 134217728 } },
  metrics: { rewritten_data_files_count: 24 },
  attempts: [
    attempt({
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
      job_name: "tm-orders-rewrite-a1",
    }),
    attempt({
      attempt: 2,
      size: "M",
      status: "succeeded",
      started_at: "2026-10-31T10:03:00Z",
      started_running_at: "2026-10-31T10:03:05Z",
      finished_at: "2026-10-31T10:09:00Z",
      job_name: "tm-orders-rewrite-a2",
    }),
  ],
});

const SCOPED_RUN = run({
  run_id: "mr-scoped",
  trigger: "event",
  filters: [
    { spec_id: 0, where: "(`region` = 'eu')" },
    { spec_id: 1, where: "(`region` = 'us')" },
  ],
});

// The next run of a plan whose compaction is still running.
const PENDING_RUN = run({
  run_id: "mr-pending",
  operation: "rewrite_manifests",
  status: "pending",
  started_at: null,
  finished_at: null,
  attempts: [],
});

const SKIPPED_RUN = run({
  run_id: "mr-skipped",
  operation: "remove_orphan_files",
  status: "skipped",
  started_at: null,
  finished_at: "2026-10-31T10:05:00Z",
  skip_reason: "the table's maintenance stopped before this run started",
  attempts: [],
});

const OLDER_RUN_ID = "mr-older";
const OLDER_RUN = run({ run_id: OLDER_RUN_ID, operation: "expire_snapshots", trigger: "scheduled" });

function LocationProbe() {
  const location = useLocation();
  return <output aria-label="search">{location.search}</output>;
}

function renderTab(route = "/") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>
        <MaintenanceTab tableUuid="uuid-orders" />
        <LocationProbe />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const search = () => screen.getByRole("status", { name: "search" }).textContent;

// The window at 768px and wider matches; the jsdom setup's stub matches no query (a phone).
function stubWindowWidth({ wide }: { wide: boolean }) {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: wide && query === "(min-width: 48rem)",
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  }));
}

function rowOf(button: HTMLElement): HTMLElement {
  return button.closest("tr") as HTMLElement;
}

function attemptsIn(panel: HTMLElement): HTMLElement[] {
  return within(within(panel).getByRole("list", { name: "Attempts" })).getAllByRole("listitem");
}

const markers = (items: HTMLElement[]) =>
  items.map((item) => item.querySelector("[data-marker]")?.getAttribute("data-marker"));

describe("MaintenanceTab", () => {
  let calls: StubbedCall[];

  beforeEach(() => {
    // Beside the list, as on a laptop; the phone layout has its own describe below.
    stubWindowWidth({ wide: true });
    calls = stubCatalogApi({ [`GET ${RUNS_PATH}`]: () => jsonResponse([EXPIRE_RUN, ESCALATED_RUN]) });
  });

  it("lists one row per run with its operation, trigger, status, start and duration", async () => {
    renderTab();
    const table = await screen.findByRole("table", { name: "Maintenance runs, newest first" });
    expect(within(table).getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
      "Operation",
      "Trigger",
      "Status",
      "Started",
      "Duration",
    ]);
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(2);
    expect(within(rows[0]!).getByText("Expire snapshots")).toBeInTheDocument();
    expect(within(rows[0]!).getByText("Failed")).toHaveClass("bg-negative-container");
    expect(within(rows[0]!).getByText("2m 30s")).toBeInTheDocument();
    expect(within(rows[1]!).getByText("Rewrite data files")).toBeInTheDocument();
    expect(within(rows[1]!).getByText("scheduled")).toBeInTheDocument();
    expect(within(rows[1]!).getByText("9m 0s")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open Rewrite data files run mr-escalated" })).toBeInTheDocument();
    expect(calls[0]?.path).toBe(RUNS_PATH);
  });

  it("shows the load error when the first read fails", async () => {
    calls = stubCatalogApi({ [`GET ${RUNS_PATH}`]: () => jsonResponse({ detail: "runs unavailable" }, 500) });
    renderTab();
    expect(await screen.findByText("Could not load maintenance runs: runs unavailable")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("opens a run in the panel when its row is pressed, and keeps it in the url", async () => {
    const user = userEvent.setup();
    renderTab("/?since=x");
    const row = rowOf(await screen.findByRole("button", { name: "Open Rewrite data files run mr-escalated" }));
    await user.click(within(row).getByText("Rewrite data files"));
    const panel = screen.getByRole("dialog", { name: "Rewrite data files" });
    expect(search()).toBe("?since=x&run=mr-escalated");
    expect(within(panel).getByText("mr-escalated")).toHaveClass("font-mono");
    expect(within(panel).getByText("table-maintenance:table-uuid=uuid-orders")).toHaveClass("font-mono");
    expect(within(panel).getByText("P1")).toBeInTheDocument();
    expect(within(panel).getByText("Result")).toBeInTheDocument();
    expect(within(panel).getByText("rewritten_data_files_count")).toHaveClass("font-mono");
    expect(within(panel).getByText("24")).toBeInTheDocument();
    expect(within(panel).queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Maintenance runs, newest first" })).toBeInTheDocument();
  });

  it("lists every attempt in a timeline, oldest first, each with its status, reason, next step and job", async () => {
    renderTab("/?run=mr-escalated");
    const panel = await screen.findByRole("dialog", { name: "Rewrite data files" });
    expect(within(panel).getByRole("heading", { name: "Attempts" })).toBeInTheDocument();
    const items = attemptsIn(panel);
    expect(items).toHaveLength(2);
    const [first, second] = items as [HTMLElement, HTMLElement];
    expect(within(first).getByText("Attempt 1 · S")).toBeInTheDocument();
    expect(within(first).getByText("Failed")).toHaveClass("bg-negative-container");
    expect(within(first).getByText("Out of memory")).toBeInTheDocument();
    expect(within(first).getByText("Retrying at size M")).toBeInTheDocument();
    expect(within(first).getByText("Queued 20s")).toBeInTheDocument();
    expect(within(first).getByText("Ran 1m 40s")).toBeInTheDocument();
    expect(within(first).getByText("Event log: Did not finish")).toBeInTheDocument();
    expect(within(first).getByText("tm-orders-rewrite-a1")).toHaveClass("font-mono");
    expect(within(second).getByText("Attempt 2 · M")).toBeInTheDocument();
    expect(within(second).getByText("Succeeded")).toBeInTheDocument();
    expect(within(second).getByText("Done")).toBeInTheDocument();
    expect(markers(items)).toEqual(["outlined", "outlined"]);
  });

  it("says which partitions a compaction passed to rewrite_data_files, each spec on its own line", async () => {
    calls = stubCatalogApi({ [`GET ${RUNS_PATH}`]: () => jsonResponse([SCOPED_RUN]) });
    renderTab("/?run=mr-scoped");
    const panel = await screen.findByRole("dialog", { name: "Rewrite data files" });
    expect(within(panel).getByText("Scope")).toBeInTheDocument();
    expect(within(panel).getByText("Partitions over the target")).toBeInTheDocument();
    expect(within(panel).getByText("spec 0: (`region` = 'eu')")).toHaveClass("break-all");
    expect(within(panel).getByText("spec 1: (`region` = 'us')")).toBeInTheDocument();
  });

  it("says a compaction with no filters covers the whole table", async () => {
    renderTab("/?run=mr-escalated");
    const panel = await screen.findByRole("dialog", { name: "Rewrite data files" });
    expect(within(panel).getByText("Whole table")).toBeInTheDocument();
    expect(within(panel).queryByText(/^spec \d+:/)).not.toBeInTheDocument();
  });

  it("shows an expiry's parameters and error, and no scope or result", async () => {
    renderTab("/?run=mr-expire");
    const panel = await screen.findByRole("dialog", { name: "Expire snapshots" });
    expect(within(panel).queryByText("Scope")).not.toBeInTheDocument();
    expect(within(panel).getByText("Parameters")).toBeInTheDocument();
    expect(within(panel).getByText("retain_last")).toHaveClass("font-mono");
    expect(within(panel).getByText("5")).toBeInTheDocument();
    expect(within(panel).getByText("older_than")).toBeInTheDocument();
    expect(within(panel).getByText('"2026-10-26T10:00:00+00:00"')).toBeInTheDocument();
    expect(within(panel).queryByText("Result")).not.toBeInTheDocument();
    expect(within(panel).getByText("snapshot store unreachable")).toHaveClass("text-negative-text");
  });

  it("leaves out the parameters and the error when the run has none", async () => {
    calls = stubCatalogApi({ [`GET ${RUNS_PATH}`]: () => jsonResponse([SCOPED_RUN]) });
    renderTab("/?run=mr-scoped");
    const panel = await screen.findByRole("dialog", { name: "Rewrite data files" });
    expect(within(panel).queryByText("Parameters")).not.toBeInTheDocument();
    expect(within(panel).queryByText("Error")).not.toBeInTheDocument();
    expect(within(panel).queryByText("Skipped")).not.toBeInTheDocument();
  });

  it("says a pending run has not started and waits for the runs before it", async () => {
    calls = stubCatalogApi({ [`GET ${RUNS_PATH}`]: () => jsonResponse([PENDING_RUN, ESCALATED_RUN]) });
    renderTab("/?run=mr-pending");
    const row = rowOf(await screen.findByRole("button", { name: "Open Rewrite manifests run mr-pending" }));
    expect(within(row).getAllByRole("cell").map((cell) => cell.textContent)).toEqual([
      "Rewrite manifests",
      "manual",
      "Pending",
      "—",
      "—",
    ]);
    const panel = screen.getByRole("dialog", { name: "Rewrite manifests" });
    expect(within(panel).getByText("No attempt yet. This run waits for the runs before it.")).toBeInTheDocument();
    expect(within(panel).queryByRole("list", { name: "Attempts" })).not.toBeInTheDocument();
    expect(within(panel).getByText("Started").nextElementSibling).toHaveTextContent(/^—$/);
  });

  it("says why a skipped run was skipped", async () => {
    calls = stubCatalogApi({ [`GET ${RUNS_PATH}`]: () => jsonResponse([SKIPPED_RUN]) });
    renderTab("/?run=mr-skipped");
    const panel = await screen.findByRole("dialog", { name: "Remove orphan files" });
    expect(within(panel).getByText("Skipped", { selector: "dt" }).nextElementSibling).toHaveTextContent(
      "the table's maintenance stopped before this run started",
    );
    expect(within(panel).queryByText(/^No attempt yet/)).not.toBeInTheDocument();
  });

  describe("beside the list, at 768px and wider", () => {
    it("shows another run in the same panel when its row is pressed, and moves focus to the heading", async () => {
      const user = userEvent.setup();
      renderTab();
      await user.click(await screen.findByRole("button", { name: "Open Expire snapshots run mr-expire" }));
      expect(screen.getByRole("dialog", { name: "Expire snapshots" })).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Open Rewrite data files run mr-escalated" }));
      const dialogs = screen.getAllByRole("dialog");
      expect(dialogs).toHaveLength(1);
      expect(dialogs[0]).toHaveAccessibleName("Rewrite data files");
      expect(search()).toBe("?run=mr-escalated");
      await waitFor(() => expect(screen.getByRole("heading", { name: "Rewrite data files" })).toHaveFocus());
      expect(screen.getByRole("button", { name: "Open Rewrite data files run mr-escalated" })).toHaveAttribute(
        "aria-expanded",
        "true",
      );
    });

    it("closes on Escape, drops the run from the url and returns focus to the row that opened it", async () => {
      const user = userEvent.setup();
      renderTab("/?since=x");
      await user.click(await screen.findByRole("button", { name: "Open Expire snapshots run mr-expire" }));
      await user.click(screen.getByRole("button", { name: "Open Rewrite data files run mr-escalated" }));
      await user.keyboard("{Escape}");
      await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
      expect(search()).toBe("?since=x");
      await waitFor(() =>
        expect(screen.getByRole("button", { name: "Open Rewrite data files run mr-escalated" })).toHaveFocus(),
      );
    });

    it("opens a run from the keyboard and moves focus to the panel's heading", async () => {
      const user = userEvent.setup();
      renderTab();
      await screen.findByRole("table");
      await user.tab();
      expect(screen.getByRole("link", { name: "Running workflows in Temporal" })).toHaveFocus();
      await user.tab();
      await user.tab();
      const open = screen.getByRole("button", { name: "Open Expire snapshots run mr-expire" });
      expect(open).toHaveFocus();
      await user.keyboard("{Enter}");
      await waitFor(() => expect(screen.getByRole("heading", { name: "Expire snapshots" })).toHaveFocus());
      expect(open).toHaveAttribute("aria-expanded", "true");
    });
  });

  describe("below 768px", () => {
    it("opens the run as a modal panel and returns focus to its row on Escape", async () => {
      stubWindowWidth({ wide: false });
      const user = userEvent.setup();
      renderTab();
      const open = await screen.findByRole("button", { name: "Open Expire snapshots run mr-expire" });
      await user.click(open);
      const panel = screen.getByRole("dialog", { name: "Expire snapshots" });
      await waitFor(() => expect(panel).toContainElement(document.activeElement as HTMLElement));
      expect(screen.queryByRole("table")).not.toBeInTheDocument();
      await user.keyboard("{Escape}");
      await waitFor(() => expect(open).toHaveFocus());
      expect(search()).toBe("");
    });
  });

  describe("a run that is not in the loaded list", () => {
    beforeEach(() => {
      calls = stubCatalogApi({
        [`GET ${RUNS_PATH}`]: () => jsonResponse([EXPIRE_RUN]),
        [`GET ${runPath(OLDER_RUN_ID)}`]: () => jsonResponse(OLDER_RUN),
        [`GET ${runPath("mr-other")}`]: () => jsonResponse(run({ run_id: "mr-other", table_uuid: "uuid-customers" })),
        [`GET ${runPath("mr-gone")}`]: () => jsonResponse({ detail: "run mr-gone not found" }, 404),
        [`GET ${runPath("run-42")}`]: () => jsonResponse({ detail: "not an mr- id" }, 422),
        [`GET ${runPath("mr-slow")}`]: () => new Promise<Response>(() => {}),
      });
    });

    it("reads it by id and opens it", async () => {
      renderTab(`/?run=${OLDER_RUN_ID}`);
      const panel = await screen.findByRole("dialog", { name: "Expire snapshots" });
      expect(within(panel).getByText(OLDER_RUN_ID)).toBeInTheDocument();
      expect(callsTo(calls, "GET", runPath(OLDER_RUN_ID))).toHaveLength(1);
    });

    it("does not read a listed run again by id", async () => {
      renderTab("/?run=mr-expire");
      await screen.findByRole("dialog", { name: "Expire snapshots" });
      expect(calls.filter((call) => call.path.startsWith("/v1/table-maintenance-runs/"))).toHaveLength(0);
    });

    it("shows a loading state in the panel while it is read", async () => {
      renderTab("/?run=mr-slow");
      const panel = await screen.findByRole("dialog");
      expect(within(panel).getByText("Loading run…")).toBeInTheDocument();
    });

    it.each([
      ["a run that no longer exists (404)", "mr-gone"],
      ["a malformed or pre-prefix id (422)", "run-42"],
    ])("says %s is no longer available, inside the panel", async (_what, id) => {
      renderTab(`/?run=${id}`);
      const panel = await screen.findByRole("dialog");
      expect(await within(panel).findByText("This run is no longer available")).toBeInTheDocument();
      expect(screen.getByRole("table", { name: "Maintenance runs, newest first" })).toBeInTheDocument();
      expect(screen.queryByText(/^Could not/)).not.toBeInTheDocument();
    });

    it("says a run of another table belongs to another table", async () => {
      renderTab("/?run=mr-other");
      const panel = await screen.findByRole("dialog");
      expect(await within(panel).findByText("This run belongs to another table")).toBeInTheDocument();
      expect(within(panel).queryByText("mr-other")).not.toBeInTheDocument();
    });

    describe("read again while it is in flight", () => {
      const FAKE_TIMERS: Parameters<typeof vi.useFakeTimers>[0] = {
        toFake: ["setTimeout", "setInterval", "clearTimeout", "clearInterval", "Date"],
        shouldAdvanceTime: true,
      };
      const byIdReads = (id: string) => callsTo(calls, "GET", runPath(id)).length;

      afterEach(() => {
        vi.useRealTimers();
      });

      it.each(["pending", "queued", "running"])("reads a %s run again on the in-flight interval", async (status) => {
        vi.useFakeTimers(FAKE_TIMERS);
        calls = stubCatalogApi({
          [`GET ${RUNS_PATH}`]: () => jsonResponse([EXPIRE_RUN]),
          [`GET ${runPath(OLDER_RUN_ID)}`]: () => jsonResponse({ ...OLDER_RUN, status, finished_at: null }),
        });
        renderTab(`/?run=${OLDER_RUN_ID}`);
        await screen.findByRole("dialog", { name: "Expire snapshots" });
        expect(byIdReads(OLDER_RUN_ID)).toBe(1);
        await vi.advanceTimersByTimeAsync(15_500);
        await vi.waitFor(() => expect(byIdReads(OLDER_RUN_ID)).toBeGreaterThanOrEqual(2));
      });

      it("does not read a finished run again", async () => {
        vi.useFakeTimers(FAKE_TIMERS);
        renderTab(`/?run=${OLDER_RUN_ID}`);
        await screen.findByRole("dialog", { name: "Expire snapshots" });
        await vi.advanceTimersByTimeAsync(31_000);
        expect(byIdReads(OLDER_RUN_ID)).toBe(1);
      });
    });
  });

  describe("with a run in flight", () => {
    const NOW = new Date("2026-11-20T10:10:00Z");

    const inFlightAttempt = (overrides: Partial<TableMaintenanceRunAttemptApiResponse>) =>
      attempt({ event_log_finished: null, next_step: null, finished_at: null, ...overrides });

    const IN_FLIGHT = run({
      run_id: "mr-live",
      status: "running",
      started_at: "2026-11-19T10:00:00Z",
      finished_at: null,
      attempts: [
        inFlightAttempt({
          attempt: 1,
          status: "failed",
          started_at: "2026-11-19T10:00:00Z",
          started_running_at: null,
          finished_at: "2026-11-20T10:00:00Z",
          failure_class: "queue_timeout",
          next_step: "not_retried",
        }),
        inFlightAttempt({
          attempt: 2,
          status: "running",
          started_at: "2026-11-20T09:55:00Z",
          started_running_at: "2026-11-20T10:03:00Z",
        }),
        inFlightAttempt({ attempt: 3, status: "queued", started_at: "2026-11-20T10:05:00Z", started_running_at: null }),
      ],
    });

    const runReads = () => calls.filter((call) => call.method === "GET" && call.path === RUNS_PATH).length;

    afterEach(() => {
      vi.useRealTimers();
    });

    it("shows a queued attempt waiting, a running one counting and a queue timeout never running", async () => {
      vi.useFakeTimers({ now: NOW, toFake: ["Date"] });
      calls = stubCatalogApi({ [`GET ${RUNS_PATH}`]: () => jsonResponse([IN_FLIGHT]) });
      renderTab("/?run=mr-live");
      const panel = await screen.findByRole("dialog", { name: "Rewrite data files" });
      const [timedOut, running, queued] = attemptsIn(panel) as [HTMLElement, HTMLElement, HTMLElement];
      expect(within(timedOut).getByText("Queued 24h 0m")).toBeInTheDocument();
      expect(within(timedOut).getByText("Ran —")).toBeInTheDocument();
      expect(within(timedOut).getByText("Waited too long in the queue")).toBeInTheDocument();
      expect(within(running).getByText("Queued 8m 0s")).toBeInTheDocument();
      expect(within(running).getByText("Ran 7m 0s (running)")).toBeInTheDocument();
      expect(within(queued).getByText("Queued 5m 0s (waiting)")).toBeInTheDocument();
      expect(within(queued).getByText("Queued", { selector: "span" })).toHaveClass("bg-surface-container-dim");
    });

    it("fills the marker of the attempts in flight only", async () => {
      calls = stubCatalogApi({ [`GET ${RUNS_PATH}`]: () => jsonResponse([IN_FLIGHT]) });
      renderTab("/?run=mr-live");
      const panel = await screen.findByRole("dialog", { name: "Rewrite data files" });
      expect(markers(attemptsIn(panel))).toEqual(["outlined", "filled", "filled"]);
    });

    it("reads the runs again while one is in flight, so the counters move", async () => {
      vi.useFakeTimers({ toFake: ["setTimeout", "setInterval", "clearTimeout", "clearInterval", "Date"], shouldAdvanceTime: true });
      calls = stubCatalogApi({ [`GET ${RUNS_PATH}`]: () => jsonResponse([IN_FLIGHT]) });
      renderTab();
      await screen.findByRole("table");
      expect(runReads()).toBe(1);
      await vi.advanceTimersByTimeAsync(15_500);
      await vi.waitFor(() => expect(runReads()).toBeGreaterThanOrEqual(2));
    });

    it("reads the runs again while a run waits pending", async () => {
      vi.useFakeTimers({ toFake: ["setTimeout", "setInterval", "clearTimeout", "clearInterval", "Date"], shouldAdvanceTime: true });
      calls = stubCatalogApi({ [`GET ${RUNS_PATH}`]: () => jsonResponse([PENDING_RUN, ESCALATED_RUN]) });
      renderTab();
      await screen.findByRole("table");
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

      it("keeps the open run's panel across a refetch that succeeds", async () => {
        vi.useFakeTimers(FAKE_TIMERS);
        readsAnswering(ok, ok);
        renderTab("/?run=mr-live");
        await screen.findByRole("dialog", { name: "Rewrite data files" });
        await vi.advanceTimersByTimeAsync(15_500);
        await vi.waitFor(() => expect(runReads()).toBeGreaterThanOrEqual(2));
        expect(screen.getByRole("dialog", { name: "Rewrite data files" })).toBeInTheDocument();
        expect(screen.queryByText(REFRESH_FAILED)).not.toBeInTheDocument();
      });

      it("keeps the table and the panel when a refetch fails, and drops the note once one succeeds", async () => {
        vi.useFakeTimers(FAKE_TIMERS);
        readsAnswering(ok, failing, ok);
        renderTab("/?run=mr-live");
        await screen.findByRole("dialog", { name: "Rewrite data files" });
        await vi.advanceTimersByTimeAsync(15_500);
        expect(await screen.findByText(REFRESH_FAILED)).toBeInTheDocument();
        expect(screen.queryByText(/^Could not load maintenance runs/)).not.toBeInTheDocument();
        expect(screen.getByRole("dialog", { name: "Rewrite data files" })).toBeInTheDocument();
        await vi.advanceTimersByTimeAsync(15_500);
        await vi.waitFor(() => expect(screen.queryByText(REFRESH_FAILED)).not.toBeInTheDocument());
        expect(screen.getByRole("dialog", { name: "Rewrite data files" })).toBeInTheDocument();
      });
    });

    it("does not read the runs again when every one has ended", async () => {
      vi.useFakeTimers({ toFake: ["setTimeout", "setInterval", "clearTimeout", "clearInterval", "Date"], shouldAdvanceTime: true });
      calls = stubCatalogApi({ [`GET ${RUNS_PATH}`]: () => jsonResponse([ESCALATED_RUN, SKIPPED_RUN]) });
      renderTab();
      await screen.findByRole("table");
      await vi.advanceTimersByTimeAsync(60_000);
      expect(runReads()).toBe(1);
    });
  });
});
