import type { TableCommitApiResponse } from "../api/types";
import { formatCount, formatRelativeTime } from "../format";
import { hourlyCommitBuckets, writerMix } from "../freshness";

const WRITER_LABELS: Record<string, string> = {
  kafka_connect: "Kafka Connect",
  spark: "Spark",
  unknown: "Unknown",
};

const FALLBACK_COLOR = "#8c959f";

const OPERATION_COLORS: Record<string, string> = {
  append: "#2da44e",
  overwrite: "#bf8700",
  delete: "#cf222e",
  replace: "#0969da",
};

const WIDTH = 480;
const HEIGHT = 120;
const BAR_GAP = 2;

interface Props {
  commits: TableCommitApiResponse[];
  truncated: boolean;
  now: Date;
  lastCommittedAt: string | null;
}

export function FreshnessPanel({ commits, truncated, now, lastCommittedAt }: Props) {
  const buckets = hourlyCommitBuckets(commits, now);
  const totals = buckets.map((b) => Object.values(b.byOperation).reduce((a, c) => a + c, 0));
  const peak = Math.max(1, ...totals);
  const barWidth = WIDTH / buckets.length;
  const prefix = truncated ? "≥ " : "";
  const mix = Object.entries(writerMix(commits));
  const operations = [...new Set(buckets.flatMap((b) => Object.keys(b.byOperation)))];
  const newest = [...commits].sort((a, b) => b.committed_at.localeCompare(a.committed_at))[0];
  return (
    <section className="panel" aria-label="Freshness">
      <h2>Freshness &amp; activity</h2>
      <p>
        {lastCommittedAt === null
          ? "Last commit: none"
          : `Last commit ${formatRelativeTime(lastCommittedAt, now)}`}
        {newest !== undefined && lastCommittedAt !== null && (
          <span className="muted">{` by ${WRITER_LABELS[newest.writer] ?? newest.writer}`}</span>
        )}
      </p>
      <p>{`${prefix}${formatCount(commits.length)} commits in the last 24 h`}</p>
      <svg
        role="img"
        aria-label="Commits per hour over the last 24 hours"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="commit-chart"
      >
        {buckets.map((bucket, index) => {
          let y = HEIGHT;
          return (
            <g key={bucket.hourStart}>
              <title>{`${bucket.hourStart}: ${totals[index]} commits`}</title>
              {Object.entries(bucket.byOperation).map(([operation, count]) => {
                const height = (count / peak) * (HEIGHT - 4);
                y -= height;
                return (
                  <rect
                    key={operation}
                    x={index * barWidth + BAR_GAP / 2}
                    y={y}
                    width={barWidth - BAR_GAP}
                    height={height}
                    fill={OPERATION_COLORS[operation] ?? FALLBACK_COLOR}
                  />
                );
              })}
            </g>
          );
        })}
      </svg>
      {operations.length > 0 && (
        <ul className="legend">
          {operations.map((operation) => (
            <li key={operation}>
              <span
                className="swatch"
                style={{ background: OPERATION_COLORS[operation] ?? FALLBACK_COLOR }}
              />
              {operation}
            </li>
          ))}
        </ul>
      )}
      {mix.length > 0 && (
        <p className="muted">
          {`Writers: ${mix
            .map(
              ([writer, count]) =>
                `${WRITER_LABELS[writer] ?? writer} ${prefix}${formatCount(count)}`,
            )
            .join(", ")}`}
        </p>
      )}
    </section>
  );
}
