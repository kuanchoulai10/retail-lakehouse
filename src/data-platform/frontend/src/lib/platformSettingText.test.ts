import { describe, expect, it } from "vitest";
import type { PlatformSettingApiResponse } from "@/api/generated/model";
import { platformSettingText } from "./platformSettingText";

function item(value: number | string, unit: string | null): PlatformSettingApiResponse {
  return { key: "k", label: "L", value, unit, description: "D." };
}

describe("platformSettingText", () => {
  it("reads whole minutes, hours and days of seconds in the larger unit and keeps the exact seconds", () => {
    expect(platformSettingText(item(120, "seconds"))).toEqual({ value: "2 min", exact: "120 seconds" });
    expect(platformSettingText(item(21_600, "seconds"))).toEqual({ value: "6 h", exact: "21,600 seconds" });
    expect(platformSettingText(item(86_400, "seconds"))).toEqual({ value: "1 d", exact: "86,400 seconds" });
  });

  it("says seconds that are not a whole minute as seconds, with nothing to add", () => {
    expect(platformSettingText(item(90, "seconds"))).toEqual({ value: "90 seconds", exact: null });
    expect(platformSettingText(item(45, "seconds"))).toEqual({ value: "45 seconds", exact: null });
  });

  it("reads bytes in a larger unit and keeps the exact count", () => {
    expect(platformSettingText(item(1_073_741_824, "bytes"))).toEqual({
      value: "1.0 GB",
      exact: "1,073,741,824 bytes",
    });
    expect(platformSettingText(item(0, "bytes"))).toEqual({ value: "0 bytes", exact: null });
  });

  it("puts a count before its unit", () => {
    expect(platformSettingText(item(10_000, "partitions"))).toEqual({ value: "10,000 partitions", exact: null });
    expect(platformSettingText(item(2, "operations"))).toEqual({ value: "2 operations", exact: null });
  });

  it("writes GB·hours to two decimals", () => {
    expect(platformSettingText(item(0.05, "GB·hours"))).toEqual({ value: "0.05 GB·hours", exact: null });
  });

  it("shows a value that carries its own unit as it is", () => {
    expect(platformSettingText(item("768m", null))).toEqual({ value: "768m", exact: null });
  });

  it("shows a weight as a multiplier", () => {
    expect(platformSettingText(item(4, "times"))).toEqual({ value: "4 times", exact: null });
  });
});
