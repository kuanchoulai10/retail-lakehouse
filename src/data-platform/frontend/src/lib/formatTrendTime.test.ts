import { describe, expect, it } from "vitest";
import { formatTrendTime } from "./formatTrendTime";

// Local times, so the clock reads the same in any time zone.
const AT = new Date(2026, 10, 20, 9, 5, 30).toISOString();

describe("formatTrendTime", () => {
  it("shows seconds at 1h, whose 30 s steps would otherwise share a minute", () => {
    expect(formatTrendTime(AT, "1h")).toBe("09:05:30");
  });

  it.each(["3h", "6h"] as const)("shows hours and minutes at %s", (range) => {
    expect(formatTrendTime(AT, range)).toBe("09:05");
  });

  it("leaves a value that is not a time as it is", () => {
    expect(formatTrendTime("soon", "6h")).toBe("soon");
  });
});
