import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import type { TableCommitApiResponse } from "@/api/types";
import { Panel } from "@/components/Panel";
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { formatCount, formatRelativeTime } from "@/format";
import { hourlyCommitBuckets, writerMix } from "@/freshness";
import { writerLabel } from "@/writerLabel";

const OPERATION_STEPS: Record<string, string> = {
  append: "var(--chart-1)",
  overwrite: "var(--chart-2)",
  delete: "var(--chart-3)",
  replace: "var(--chart-4)",
};
const FALLBACK_STEP = "var(--chart-5)";

interface Props {
  commits: TableCommitApiResponse[];
  truncated: boolean;
  now: Date;
  lastCommittedAt: string | null;
}

function hourLabel(hourStart: string): string {
  return new Date(hourStart).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function FreshnessPanel({ commits, truncated, now, lastCommittedAt }: Props) {
  const buckets = hourlyCommitBuckets(commits, now);
  const prefix = truncated ? "≥ " : "";
  const mix = Object.entries(writerMix(commits));
  const operations = [...new Set(buckets.flatMap((b) => Object.keys(b.byOperation)))];
  const config: ChartConfig = Object.fromEntries(
    operations.map((operation) => [
      operation,
      { label: operation, color: OPERATION_STEPS[operation] ?? FALLBACK_STEP },
    ]),
  );
  const data = buckets.map((bucket) => ({
    hourStart: bucket.hourStart,
    ...bucket.byOperation,
  }));
  const newest = [...commits].sort((a, b) => b.committed_at.localeCompare(a.committed_at))[0];
  return (
    <Panel title="Freshness & activity">
      <div className="space-y-1 p-4 pb-0 text-sm">
        <p>
          {lastCommittedAt === null
            ? "Last commit: none"
            : `Last commit ${formatRelativeTime(lastCommittedAt, now)}`}
          {newest !== undefined && lastCommittedAt !== null && (
            <span className="text-muted-foreground">{` by ${writerLabel(newest.writer)}`}</span>
          )}
        </p>
        <p className={truncated ? "tabular-nums text-warning" : "tabular-nums"}>
          {`${prefix}${formatCount(commits.length)} commits in the last 24 h`}
        </p>
      </div>
      <div className="p-4">
        <ChartContainer
          config={config}
          className="aspect-auto h-32 w-full"
          role="img"
          aria-label="Commits per hour over the last 24 hours"
        >
          <BarChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="hourStart"
              tickLine={false}
              axisLine={false}
              interval={5}
              tickFormatter={hourLabel}
            />
            <YAxis hide allowDecimals={false} />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  labelFormatter={(_, items) =>
                    hourLabel(String(items[0]?.payload?.hourStart ?? ""))
                  }
                />
              }
            />
            {operations.map((operation) => (
              <Bar
                key={operation}
                dataKey={operation}
                stackId="commits"
                fill={`var(--color-${operation})`}
                isAnimationActive={false}
              />
            ))}
          </BarChart>
        </ChartContainer>
        {operations.length > 0 && (
          <ul aria-label="Operations" className="mt-2 flex flex-wrap gap-4 text-[13px]">
            {operations.map((operation) => (
              <li key={operation} className="flex items-center gap-1.5 font-mono">
                <span
                  aria-hidden
                  className="size-2.5 rounded-sm"
                  style={{ background: OPERATION_STEPS[operation] ?? FALLBACK_STEP }}
                />
                {operation}
              </li>
            ))}
          </ul>
        )}
      </div>
      {mix.length > 0 && (
        <p className="border-t border-border px-4 py-2.5 text-[13px] text-muted-foreground">
          {`Writers: ${mix
            .map(([writer, count]) => `${writerLabel(writer)} ${prefix}${formatCount(count)}`)
            .join(", ")}`}
        </p>
      )}
    </Panel>
  );
}
