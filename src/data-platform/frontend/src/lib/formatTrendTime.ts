import type { GetTableMetricTrendsRange } from "@/api/generated/model";

// A trend point's local clock time. The 1h window steps every 30 s, so it shows seconds, or two
// neighbouring points would read the same.
export function formatTrendTime(value: unknown, range: GetTableMetricTrendsRange): string {
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    ...(range === "1h" && { second: "2-digit" }),
    hourCycle: "h23",
  });
}
