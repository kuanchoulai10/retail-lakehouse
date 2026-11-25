import { describe, expect, it } from "vitest";
import { isInFlightStatus } from "./isInFlightStatus";

describe("isInFlightStatus", () => {
  it.each(["pending", "queued", "running"])("counts a %s run as in flight", (status) => {
    expect(isInFlightStatus(status)).toBe(true);
  });

  it("counts a run waiting to retry as still in flight", () => {
    expect(isInFlightStatus("retry_waiting")).toBe(true);
  });

  it.each(["succeeded", "failed", "skipped", "cancelled"])("does not count a %s run as in flight", (status) => {
    expect(isInFlightStatus(status)).toBe(false);
  });
});
