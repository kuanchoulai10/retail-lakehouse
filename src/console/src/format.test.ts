import { describe, expect, it } from "vitest";
import { formatBytes, formatCount, formatRelativeTime, formatSeconds } from "./format";

describe("formatBytes", () => {
  it("formats bytes in binary units", () => {
    expect(formatBytes(50540544)).toBe("48.2 MB");
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
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
