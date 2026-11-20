import { describe, expect, it } from "vitest";
import { formatBytes, formatCount, formatDuration, formatGbHours, formatRelativeTime, formatSeconds } from "./format";

describe("formatBytes", () => {
  it("formats bytes in binary units", () => {
    expect(formatBytes(50540544)).toBe("48.2 MB");
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
  });
});

describe("formatGbHours", () => {
  it("shows two decimals", () => {
    expect(formatGbHours(1.5)).toBe("1.50");
    expect(formatGbHours(0.05)).toBe("0.05");
  });

  it("shows an amount too small to round as below one hundredth, and none as zero", () => {
    expect(formatGbHours(0.0005)).toBe("< 0.01");
    expect(formatGbHours(0)).toBe("0.00");
  });
});

describe("formatCount", () => {
  it("groups thousands and dashes null", () => {
    expect(formatCount(1204331)).toBe("1,204,331");
    expect(formatCount(null)).toBe("—");
  });
});

describe("formatRelativeTime", () => {
  const now = new Date("2026-10-31T12:00:00Z");
  it("renders elapsed time in the largest unit", () => {
    expect(formatRelativeTime("2026-10-31T11:59:30Z", now)).toBe("just now");
    expect(formatRelativeTime("2026-10-31T11:45:00Z", now)).toBe("15 min ago");
    expect(formatRelativeTime("2026-10-31T09:00:00Z", now)).toBe("3 h ago");
    expect(formatRelativeTime("2026-10-28T12:00:00Z", now)).toBe("3 d ago");
  });
  it("dashes a missing time", () => {
    expect(formatRelativeTime(null, now)).toBe("—");
  });
});

describe("formatSeconds", () => {
  it("uses the largest whole unit", () => {
    expect(formatSeconds(604800)).toBe("7 d");
    expect(formatSeconds(86400)).toBe("1 d");
    expect(formatSeconds(21600)).toBe("6 h");
    expect(formatSeconds(300)).toBe("5 min");
    expect(formatSeconds(90)).toBe("90 s");
  });
});

describe("formatDuration", () => {
  const START = "2026-11-20T10:00:00Z";
  const after = (seconds: number) => new Date(Date.parse(START) + seconds * 1000).toISOString();

  it.each([
    [0, "0s"],
    [45, "45s"],
    [60, "1m 0s"],
    [150, "2m 30s"],
    [3599, "59m 59s"],
  ])("shows %i seconds as %s under an hour", (seconds, text) => {
    expect(formatDuration(START, after(seconds))).toBe(text);
  });

  it.each([
    [3600, "1h 0m"],
    [3900, "1h 5m"],
    [86_399, "23h 59m"],
    [86_400, "24h 0m"],
    [90_000, "25h 0m"],
  ])("shows %i seconds as %s from an hour on", (seconds, text) => {
    expect(formatDuration(START, after(seconds))).toBe(text);
  });

  it("is a dash without an end or when the end precedes the start", () => {
    expect(formatDuration(START, null)).toBe("—");
    expect(formatDuration(START, after(-1))).toBe("—");
  });
});
