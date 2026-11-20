import type { MetricCardDelta } from "@retail-lakehouse/design-system";
import type { TableMetricTrendsApiResponse } from "@/api/generated/model";
import { formatCount } from "@/format";

export type MetricTrendRow = { time: string } & Record<string, number | null>;

// One chart row per trend point, in order, keyed by `time`; a gap stays null so the chart breaks there.
export function metricTrendRows(trends: TableMetricTrendsApiResponse): MetricTrendRow[] {
  return trends.points.map((point) => ({ ...point.values, time: point.at }) as MetricTrendRow);
}

// How far a metric moved in the window: the first value the window holds against the current one.
// Always neutral, since a metric going up or down is not good or bad by itself.
export function metricDelta(
  trends: TableMetricTrendsApiResponse,
  key: string,
  current: number,
  rangeLabel: string,
  format: (value: number) => string = formatCount,
): MetricCardDelta | undefined {
  const first = trends.points.map((point) => point.values[key]).find((value) => value !== null && value !== undefined);
  if (first === undefined || first === null) return undefined;
  const change = current - first;
  if (change === 0) return { text: `No change in ${rangeLabel}`, direction: "flat", tone: "neutral" };
  return change > 0
    ? { text: `+${format(change)} in ${rangeLabel}`, direction: "up", tone: "neutral" }
    : { text: `−${format(-change)} in ${rangeLabel}`, direction: "down", tone: "neutral" };
}
