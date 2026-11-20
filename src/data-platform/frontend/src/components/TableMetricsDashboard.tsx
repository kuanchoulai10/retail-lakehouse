import {
  AreaChart,
  LineChart,
  MetricCard,
  Panel,
  TimeRangePicker,
  type ChartSeries,
  type TimeRangeOption,
} from "@retail-lakehouse/design-system";
import type { ReactNode } from "react";
import type { GetTableMetricTrendsRange, TableMetricValuesApiResponse } from "@/api/generated/model";
import { useGetTableCurrentMetrics, useGetTableMetricTrends } from "@/api/generated/tables/tables";
import { useMetricRange } from "@/components/tabs/useMetricRange";
import { errorMessage, formatBytes, formatCount } from "@/format";
import { formatTrendTime } from "@/lib/formatTrendTime";
import { metricDelta, metricTrendRows, type MetricTrendRow } from "@/lib/metricTrendRows";

const REFETCH_MS = 60_000;

const RANGES: readonly TimeRangeOption[] = [
  { value: "1h", label: "1h", description: "Last 1 hour" },
  { value: "3h", label: "3h", description: "Last 3 hours" },
  { value: "6h", label: "6h", description: "Last 6 hours" },
];

const RANGE_TEXT: Record<GetTableMetricTrendsRange, string> = {
  "1h": "the last hour",
  "3h": "the last 3 hours",
  "6h": "the last 6 hours",
};

const CARDS: readonly { label: string; key: keyof TableMetricValuesApiResponse; format: (value: number) => string }[] = [
  { label: "Data files", key: "data_files", format: formatCount },
  { label: "Total size", key: "data_size_bytes", format: formatBytes },
  { label: "Total rows", key: "data_records", format: formatCount },
  { label: "Reducible files", key: "reducible_files", format: formatCount },
  { label: "Snapshots", key: "snapshots", format: formatCount },
  { label: "Manifests", key: "manifests", format: formatCount },
];

const FILES: readonly ChartSeries[] = [
  { key: "data_files", name: "Data files" },
  { key: "position_delete_files", name: "Position delete files" },
  { key: "equality_delete_files", name: "Equality delete files" },
  { key: "deletion_vectors", name: "Deletion vectors" },
];
const SIZE: readonly ChartSeries[] = [{ key: "data_size_bytes", name: "Total size" }];
const ROWS: readonly ChartSeries[] = [
  { key: "data_records", name: "Total rows" },
  { key: "position_delete_records", name: "Position delete rows" },
  { key: "equality_delete_records", name: "Equality delete rows" },
];
const REDUCIBLE: readonly ChartSeries[] = [{ key: "reducible_files", name: "Reducible files" }];
const MANIFESTS: readonly ChartSeries[] = [
  { key: "manifests", name: "Manifests" },
  { key: "manifest_average_entries", name: "Entries per manifest" },
];
const MANIFEST_SIZE: readonly ChartSeries[] = [{ key: "manifest_average_size_bytes", name: "Average manifest size" }];
const SNAPSHOTS: readonly ChartSeries[] = [{ key: "snapshots", name: "Snapshots" }];

function numbers(rows: readonly MetricTrendRow[], key: string): number[] {
  return rows.map((row) => row[key]).filter((value): value is number => typeof value === "number");
}

// A chart none of whose series has a value in the window says so, instead of drawing empty axes.
function chartRows(rows: readonly MetricTrendRow[], series: readonly ChartSeries[]): readonly MetricTrendRow[] {
  return series.some((item) => numbers(rows, item.key).length > 0) ? rows : [];
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Panel title={title} className="min-w-0">
      <div className="flex flex-col gap-4">{children}</div>
    </Panel>
  );
}

// A managed table's metrics on its Overview: the newest values from the database as cards, and their
// trend over the chosen window from Prometheus as charts. The two load apart, so a Prometheus that
// cannot answer leaves the cards in place.
export function TableMetricsDashboard({ tableUuid }: { tableUuid: string }) {
  const { range, setRange } = useMetricRange();
  const current = useGetTableCurrentMetrics(tableUuid, { query: { refetchInterval: REFETCH_MS } });
  const trends = useGetTableMetricTrends(tableUuid, { range }, { query: { refetchInterval: REFETCH_MS } });
  const metrics = current.data?.metrics ?? null;
  const rows = trends.data === undefined ? [] : metricTrendRows(trends.data);
  const over = RANGE_TEXT[range];
  const chart = (series: readonly ChartSeries[]) => ({
    data: chartRows(rows, series),
    index: "time",
    indexFormatter: (value: unknown) => formatTrendTime(value, range),
    series,
    loading: trends.isPending,
    error: trends.isError ? `Trends unavailable: ${errorMessage(trends.error)}` : undefined,
  });

  let note: ReactNode = null;
  if (current.isError) {
    note = (
      <p role="alert" className="type-body-medium text-negative-text">
        {`Could not load the current metrics: ${errorMessage(current.error)}`}
      </p>
    );
  } else if (current.data !== undefined && metrics === null) {
    note = (
      <p className="type-body-medium text-on-surface-variant">Metrics appear after the table's next reconciliation.</p>
    );
  }

  return (
    <div className="flex min-w-0 flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        {note}
        <TimeRangePicker className="ml-auto" options={RANGES} value={range} onValueChange={setRange} />
      </div>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(10rem,1fr))] gap-3">
        {CARDS.map(({ label, key, format }) => {
          const value = metrics?.[key];
          const trend = value === undefined ? [] : numbers(rows, key);
          return (
            <MetricCard
              key={key}
              label={label}
              loading={current.isPending}
              value={value === undefined ? "—" : format(value)}
              delta={value === undefined || trends.data === undefined ? undefined : metricDelta(trends.data, key, value, range, format)}
              trend={trend.length > 0 ? trend : undefined}
              trendLabel={`${label} over ${over}`}
            />
          );
        })}
      </div>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,26rem),1fr))] gap-3">
        <Section title="Files">
          <LineChart label={`Data and delete files over ${over}`} {...chart(FILES)} />
        </Section>
        <Section title="Size">
          <AreaChart label={`Total size over ${over}`} valueFormatter={formatBytes} {...chart(SIZE)} />
        </Section>
        <Section title="Rows">
          <LineChart label={`Total and deleted rows over ${over}`} {...chart(ROWS)} />
        </Section>
        <Section title="Reducible files">
          <LineChart label={`Reducible files over ${over}`} {...chart(REDUCIBLE)} />
        </Section>
        <Section title="Manifests">
          <LineChart label={`Manifests and entries per manifest over ${over}`} {...chart(MANIFESTS)} />
          <LineChart label={`Average manifest size over ${over}`} valueFormatter={formatBytes} {...chart(MANIFEST_SIZE)} />
        </Section>
        <Section title="Snapshots">
          <LineChart label={`Snapshots over ${over}`} {...chart(SNAPSHOTS)} />
        </Section>
      </div>
    </div>
  );
}
