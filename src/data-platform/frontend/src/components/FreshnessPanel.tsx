import { CHART_COLOURS, ChartContainer, Divider, Panel } from "@retail-lakehouse/design-system";
import { Bar, BarChart, CartesianGrid, Tooltip, XAxis, YAxis } from "recharts";
import type { TableCommitApiResponse } from "@/api/generated/model";
import { formatCount, formatRelativeTime } from "@/format";
import { hourlyCommitBuckets, writerMix } from "@/freshness";
import { writerLabel } from "@/writerLabel";

const OPERATION_COLOURS: Record<string, string> = {
  append: CHART_COLOURS[0],
  overwrite: CHART_COLOURS[1],
  delete: CHART_COLOURS[2],
  replace: CHART_COLOURS[3],
};
const FALLBACK_COLOUR = CHART_COLOURS[4];

const CHART_HEIGHT = 128;

const TOOLTIP_STYLE = {
  background: "var(--color-surface)",
  border: "1px solid var(--color-outline)",
  borderRadius: "var(--radius-md)",
  color: "var(--color-on-surface)",
};

interface Props {
  commits: TableCommitApiResponse[];
  truncated: boolean;
  now: Date;
  lastCommittedAt: string | null;
}

function hourLabel(hourStart: string): string {
  return new Date(hourStart).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function colourOf(operation: string): string {
  return OPERATION_COLOURS[operation] ?? FALLBACK_COLOUR;
}

export function FreshnessPanel({ commits, truncated, now, lastCommittedAt }: Props) {
  const buckets = hourlyCommitBuckets(commits, now);
  const prefix = truncated ? "≥ " : "";
  const mix = Object.entries(writerMix(commits));
  const operations = [...new Set(buckets.flatMap((b) => Object.keys(b.byOperation)))];
  const data = buckets.map((bucket) => ({
    hourStart: bucket.hourStart,
    ...bucket.byOperation,
  }));
  const newest = [...commits].sort((a, b) => b.committed_at.localeCompare(a.committed_at))[0];
  return (
    <Panel title="Freshness & activity">
      <div className="space-y-1">
        <p>
          {lastCommittedAt === null
            ? "Last commit: none"
            : `Last commit ${formatRelativeTime(lastCommittedAt, now)}`}
          {newest !== undefined && lastCommittedAt !== null && (
            <span className="text-on-surface-variant">{` by ${writerLabel(newest.writer)}`}</span>
          )}
        </p>
        <p className={truncated ? "tabular-nums text-notice-text" : "tabular-nums"}>
          {`${prefix}${formatCount(commits.length)} commits in the last 24 h`}
        </p>
      </div>
      <div className="mt-4">
        <ChartContainer label="Commits per hour over the last 24 hours" height={CHART_HEIGHT}>
          <BarChart data={data} margin={{ top: 4, right: 16, bottom: 0, left: 16 }}>
            <CartesianGrid vertical={false} stroke="var(--color-outline-dim)" />
            <XAxis
              dataKey="hourStart"
              tickLine={false}
              axisLine={false}
              interval={5}
              tickFormatter={hourLabel}
              tick={{ fill: "currentColor", fontSize: 12 }}
            />
            <YAxis hide allowDecimals={false} />
            <Tooltip
              cursor={false}
              contentStyle={TOOLTIP_STYLE}
              labelFormatter={(label) => hourLabel(String(label))}
            />
            {operations.map((operation) => (
              <Bar
                key={operation}
                dataKey={operation}
                stackId="commits"
                fill={colourOf(operation)}
                isAnimationActive={false}
              />
            ))}
          </BarChart>
        </ChartContainer>
        {operations.length > 0 && (
          <ul aria-label="Operations" className="type-body-small mt-2 flex flex-wrap gap-4">
            {operations.map((operation) => (
              <li key={operation} className="flex items-center gap-1.5 font-mono">
                <span aria-hidden className="size-2.5 rounded-sm" style={{ background: colourOf(operation) }} />
                {operation}
              </li>
            ))}
          </ul>
        )}
      </div>
      {mix.length > 0 && (
        <>
          <Divider className="my-3" />
          <p className="type-body-small text-on-surface-variant">
            {`Writers: ${mix
              .map(([writer, count]) => `${writerLabel(writer)} ${prefix}${formatCount(count)}`)
              .join(", ")}`}
          </p>
        </>
      )}
    </Panel>
  );
}
