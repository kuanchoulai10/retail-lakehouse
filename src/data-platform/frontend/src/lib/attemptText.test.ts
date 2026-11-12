import { describe, expect, it } from "vitest";
import { eventLogText, failureClassText, nextStepText } from "./attemptText";

describe("failureClassText", () => {
  it.each([
    ["oom", "Out of memory"],
    ["timeout", "Timed out"],
    ["commit_conflict", "Conflicted with another commit"],
    ["permanent", "Retrying cannot fix it"],
    ["cancelled", "Cancelled"],
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
