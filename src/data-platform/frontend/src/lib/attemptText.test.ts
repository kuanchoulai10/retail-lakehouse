import { describe, expect, it } from "vitest";
import type { TableMaintenanceRunAttemptApiResponse } from "@/api/generated/model";
import { eventLogText, failureClassText, nextStepText, queueWaitText, runTimeText } from "./attemptText";

const NOW = new Date("2026-11-20T10:10:00Z");

function attempt(overrides: Partial<TableMaintenanceRunAttemptApiResponse>): TableMaintenanceRunAttemptApiResponse {
  return {
    attempt: 1,
    size: "S",
    status: "succeeded",
    started_at: "2026-11-20T10:00:00Z",
    started_running_at: "2026-11-20T10:03:00Z",
    finished_at: "2026-11-20T10:08:30Z",
    failure_class: null,
    error: null,
    event_log_finished: true,
    next_step: "done",
    next_size: null,
    ...overrides,
  };
}

describe("queueWaitText", () => {
  it("counts up to now and says it is still waiting for a queued attempt", () => {
    const queued = attempt({ status: "queued", started_running_at: null, finished_at: null });
    expect(queueWaitText(queued, NOW)).toBe("10m 0s (waiting)");
  });

  it("stops at the driver start once the attempt runs", () => {
    const running = attempt({ status: "running", finished_at: null });
    expect(queueWaitText(running, NOW)).toBe("3m 0s");
  });

  it("stops at the driver start for a finished attempt", () => {
    expect(queueWaitText(attempt({}), NOW)).toBe("3m 0s");
  });

  it("stops at the end of an attempt that never left the queue", () => {
    const timedOut = attempt({
      status: "failed",
      started_running_at: null,
      finished_at: "2026-11-21T10:00:00Z",
      failure_class: "queue_timeout",
    });
    expect(queueWaitText(timedOut, new Date("2026-11-22T00:00:00Z"))).toBe("1440m 0s");
  });
});

describe("runTimeText", () => {
  it("is a dash for an attempt that never ran", () => {
    const queued = attempt({ status: "queued", started_running_at: null, finished_at: null });
    expect(runTimeText(queued, NOW)).toBe("—");
    const timedOut = attempt({ status: "failed", started_running_at: null });
    expect(runTimeText(timedOut, NOW)).toBe("—");
  });

  it("counts up to now and says it is still running for a running attempt", () => {
    const running = attempt({ status: "running", finished_at: null });
    expect(runTimeText(running, NOW)).toBe("7m 0s (running)");
  });

  it("stops at the end of a finished attempt", () => {
    expect(runTimeText(attempt({}), NOW)).toBe("5m 30s");
  });
});

describe("failureClassText", () => {
  it.each([
    ["oom", "Out of memory"],
    ["timeout", "Timed out"],
    ["commit_conflict", "Conflicted with another commit"],
    ["permanent", "Retrying cannot fix it"],
    ["cancelled", "Cancelled"],
    ["queue_timeout", "Waited too long in the queue"],
    ["other", "Other error"],
  ])("says %s as %s", (failureClass, text) => {
    expect(failureClassText(failureClass)).toBe(text);
  });

  it("is empty for an attempt that did not fail", () => {
    expect(failureClassText(null)).toBe("");
  });

  it("falls back to the class name in sentence case", () => {
    expect(failureClassText("disk_full")).toBe("Disk full");
  });
});

describe("nextStepText", () => {
  it.each([
    ["done", null, "Done"],
    ["retry_larger", "M", "Retrying at size M"],
    ["retry_larger", "L", "Retrying at size L"],
    ["retry_same", "S", "Retrying at the same size"],
    ["needs_attention", null, "Stopped: needs attention"],
    ["attempts_used", null, "Stopped: no attempts left"],
    ["not_retried", null, "Stopped: retrying will not help"],
    ["cancelled", null, "Stopped: cancelled"],
    ["still_running", null, "Stopped: its job is still running"],
  ])("says %s (%s) as %s", (step, size, text) => {
    expect(nextStepText(step, size)).toBe(text);
  });

  it("is empty for a running attempt", () => {
    expect(nextStepText(null, null)).toBe("");
  });
});

describe("eventLogText", () => {
  it("says whether the event log finished", () => {
    expect(eventLogText(true)).toBe("Finished");
    expect(eventLogText(false)).toBe("Did not finish");
    expect(eventLogText(null)).toBe("Unknown");
  });
});
