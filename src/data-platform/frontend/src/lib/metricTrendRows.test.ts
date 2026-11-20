import { describe, expect, it } from "vitest";
import type { TableMetricTrendsApiResponse } from "@/api/generated/model";
import { formatBytes } from "@/format";
import { metricDelta, metricTrendRows } from "./metricTrendRows";

function trends(values: Record<string, number | null>[]): TableMetricTrendsApiResponse {
  return {
    time_range: "6h",
    start: "2026-11-20T04:00:00Z",
    end: "2026-11-20T10:00:00Z",
    step_seconds: 180,
    points: values.map((point, step) => ({
      at: new Date(Date.parse("2026-11-20T04:00:00Z") + step * 180_000).toISOString(),
      values: point,
    })),
  };
}

describe("metricTrendRows", () => {
  it("keeps every point in order, with its time and the gaps as null", () => {
    const rows = metricTrendRows(
      trends([
        { data_files: null, snapshots: null },
        { data_files: 10, snapshots: 3 },
        { data_files: null, snapshots: 4 },
      ]),
    );
    expect(rows).toEqual([
      { time: "2026-11-20T04:00:00.000Z", data_files: null, snapshots: null },
      { time: "2026-11-20T04:03:00.000Z", data_files: 10, snapshots: 3 },
      { time: "2026-11-20T04:06:00.000Z", data_files: null, snapshots: 4 },
    ]);
  });
});

describe("metricDelta", () => {
  it("compares the first value in the window with the current one, going up", () => {
    const window = trends([{ data_files: null }, { data_files: 30 }, { data_files: 40 }]);
    expect(metricDelta(window, "data_files", 42, "6h")).toEqual({ text: "+12 in 6h", direction: "up", tone: "neutral" });
  });

  it("says a drop with a real minus sign", () => {
    const window = trends([{ data_files: 20 }, { data_files: 14 }]);
    expect(metricDelta(window, "data_files", 14, "1h")).toEqual({
      text: "−6 in 1h",
      direction: "down",
      tone: "neutral",
    });
  });

  it("says no change when the value is where the window started", () => {
    const window = trends([{ snapshots: 9 }, { snapshots: 12 }, { snapshots: 9 }]);
    expect(metricDelta(window, "snapshots", 9, "3h")).toEqual({
      text: "No change in 3h",
      direction: "flat",
      tone: "neutral",
    });
  });

  it("formats the difference with the formatter it is given", () => {
    const window = trends([{ data_size_bytes: 1024 }]);
    expect(metricDelta(window, "data_size_bytes", 1024 + 2048, "6h", formatBytes)?.text).toBe("+2.0 KB in 6h");
  });

  it("gives no delta when the window holds no value", () => {
    const window = trends([{ data_files: null }, { data_files: null }]);
    expect(metricDelta(window, "data_files", 42, "6h")).toBeUndefined();
    expect(metricDelta(trends([{}]), "data_files", 42, "6h")).toBeUndefined();
  });
});
