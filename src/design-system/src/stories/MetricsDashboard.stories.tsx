import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState, type ReactNode } from "react";
import { expect, waitFor, within } from "storybook/test";
import { AreaChart } from "../components/AreaChart/AreaChart";
import { BarList } from "../components/BarList/BarList";
import { DonutChart } from "../components/DonutChart/DonutChart";
import { LineChart } from "../components/LineChart/LineChart";
import { Meter } from "../components/Meter/Meter";
import { MetricCard } from "../components/MetricCard/MetricCard";
import { TimeRangePicker } from "../components/TimeRangePicker/TimeRangePicker";
import { TooltipProvider } from "../components/Tooltip/Tooltip";
import { Tracker, type TrackerItem } from "../components/Tracker/Tracker";
import { expectNoHorizontalPageScroll } from "./assertions";
import { FILE_COUNTS, SAMPLE_TIMES, TOTAL_BYTES, formatBytes, formatSampleTime } from "./chartSamples";

const ROWS = SAMPLE_TIMES.map((time, step) => ({ time, rows: 48_200_000 + step * 310_000 }));
const REDUCIBLE = SAMPLE_TIMES.map((time, step) => ({ time, reducible: step >= 24 ? 12 + (step - 24) : 180 + step * 13 }));
const MANIFESTS = SAMPLE_TIMES.map((time, step) => ({
  time,
  manifests: step >= 24 ? 6 + Math.floor((step - 24) / 3) : 8 + Math.floor(step / 2),
  entriesPerManifest: step >= 24 ? 210 : 120 - step,
}));
const SNAPSHOTS = SAMPLE_TIMES.map((time, step) => ({ time, snapshots: step >= 30 ? 14 + (step - 30) : 20 + step }));

const OUTCOMES = { positive: "succeeded", notice: "partly succeeded", negative: "failed", neutral: "did not run" } as const;
const PATTERN: TrackerItem["status"][] = ["positive", "positive", "neutral", "positive", "notice", "positive", "positive", "negative"];
const RUNS: TrackerItem[] = Array.from({ length: 24 }, (_, hour) => {
  const status = PATTERN[hour % PATTERN.length] as TrackerItem["status"];
  return { key: `h${hour}`, status, label: `${String(hour).padStart(2, "0")}:00 — maintenance ${OUTCOMES[status]}` };
});

const RANGES = [
  { value: "1h", label: "1h", description: "Last 1 hour" },
  { value: "3h", label: "3h", description: "Last 3 hours" },
  { value: "6h", label: "6h", description: "Last 6 hours" },
];

function Section({ title, children, className }: { title: string; children: ReactNode; className?: string }) {
  return (
    <section aria-label={title} className={`flex min-w-0 flex-col gap-3 rounded-lg border border-outline bg-surface p-4 ${className ?? ""}`}>
      <h2 className="type-title-small text-on-surface">{title}</h2>
      {children}
    </section>
  );
}

function Dashboard() {
  const [range, setRange] = useState("6h");
  return (
    <TooltipProvider delayDuration={0}>
      <div className="flex flex-col gap-4 p-4">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="type-title-large text-on-surface">orders · Overview</h1>
          <TimeRangePicker options={RANGES} value={range} onValueChange={setRange} />
        </header>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(10rem,1fr))] gap-3">
          <MetricCard
            label="Data files"
            value="1,174"
            delta={{ text: "−6 in 6h", direction: "down", tone: "positive" }}
            trend={FILE_COUNTS.map((point) => point.dataFiles)}
            trendLabel="Data files, dropping after compaction"
          />
          <MetricCard
            label="Total size"
            value="4.0 GB"
            delta={{ text: "+875 MB in 6h", direction: "up", tone: "neutral" }}
            trend={TOTAL_BYTES.map((point) => point.bytes)}
            trendLabel="Total size, rising"
          />
          <MetricCard label="Total rows" value="59.1M" delta={{ text: "+10.9M in 6h", direction: "up", tone: "neutral" }} />
          <MetricCard
            label="Reducible files"
            value="23"
            delta={{ text: "−457 in 6h", direction: "down", tone: "positive" }}
            trend={REDUCIBLE.map((point) => point.reducible)}
            trendLabel="Reducible files, dropping after compaction"
          />
          <MetricCard label="Snapshots" value="19" delta={{ text: "−1 in 6h", direction: "down", tone: "neutral" }} />
          <MetricCard label="Manifests" value="9" delta={{ text: "No change in 6h", direction: "flat", tone: "neutral" }} />
        </div>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,26rem),1fr))] gap-3">
          <Section title="Files">
            <LineChart
              label="Data and delete files over the last 6 hours"
              data={FILE_COUNTS}
              index="time"
              indexFormatter={formatSampleTime}
              series={[
                { key: "dataFiles", name: "Data files" },
                { key: "positionDeletes", name: "Position deletes" },
                { key: "equalityDeletes", name: "Equality deletes" },
              ]}
            />
          </Section>
          <Section title="Size">
            <AreaChart
              label="Total size over the last 6 hours"
              data={TOTAL_BYTES}
              index="time"
              indexFormatter={formatSampleTime}
              valueFormatter={formatBytes}
              series={[{ key: "bytes", name: "Total size" }]}
            />
          </Section>
          <Section title="Reducible files">
            <LineChart
              label="Reducible files over the last 6 hours"
              data={REDUCIBLE}
              index="time"
              indexFormatter={formatSampleTime}
              series={[{ key: "reducible", name: "Reducible files" }]}
            />
          </Section>
          <Section title="Rows">
            <LineChart
              label="Total rows over the last 6 hours"
              data={ROWS}
              index="time"
              indexFormatter={formatSampleTime}
              valueFormatter={(value) => `${(value / 1_000_000).toFixed(1)}M`}
              series={[{ key: "rows", name: "Total rows" }]}
            />
          </Section>
          <Section title="Manifests">
            <LineChart
              label="Manifests and entries per manifest over the last 6 hours"
              data={MANIFESTS}
              index="time"
              indexFormatter={formatSampleTime}
              series={[
                { key: "manifests", name: "Manifests" },
                { key: "entriesPerManifest", name: "Entries per manifest" },
              ]}
            />
          </Section>
          <Section title="Snapshots">
            <LineChart
              label="Snapshots over the last 6 hours"
              data={SNAPSHOTS}
              index="time"
              indexFormatter={formatSampleTime}
              series={[{ key: "snapshots", name: "Snapshots" }]}
            />
          </Section>
        </div>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-3">
          <Section title="Storage by file kind">
            <DonutChart
              label="Storage by file kind"
              valueFormatter={formatBytes}
              centerLabel="4.0 GB"
              data={[
                { name: "Data files", value: 3.6e9 },
                { name: "Delete files", value: 2.9e8 },
                { name: "Manifests", value: 6.2e7 },
                { name: "Metadata", value: 1.1e7 },
              ]}
            />
          </Section>
          <Section title="Reducible files by partition">
            <BarList
              label="Reducible files by partition"
              items={[
                { name: "order_date=2026-11-19", value: 14 },
                { name: "order_date=2026-11-18", value: 6 },
                { name: "order_date=2026-11-17", value: 3 },
              ]}
            />
          </Section>
          <Section title="Health">
            <Meter label="Files at target size" value={94} valueText="94%" />
            <Meter label="Snapshot retention used" value={63} valueText="19 of 30" />
            <div className="flex flex-col gap-1.5">
              <p className="type-body-small text-on-surface-variant">Maintenance, last 24 hours</p>
              <Tracker label="Maintenance runs in the last 24 hours" items={RUNS} />
            </div>
          </Section>
        </div>
      </div>
    </TooltipProvider>
  );
}

const meta = {
  title: "Patterns/Table metrics dashboard",
  component: Dashboard,
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "An example of the chart widgets put together as a table's Overview dashboard " +
          "(Linear KCL-69): metric cards for the values now, trend charts grouped by topic. " +
          "Sample data only; the console builds the real page.",
      },
    },
  },
} satisfies Meta<typeof Dashboard>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Desktop: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getAllByRole("region").length).toBe(9);
    await waitFor(() => expect(canvasElement.querySelectorAll(".recharts-line-curve").length).toBeGreaterThan(5));
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  play: async ({ canvasElement }) => {
    await waitFor(() => expect(canvasElement.querySelectorAll(".recharts-line-curve").length).toBeGreaterThan(5));
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
