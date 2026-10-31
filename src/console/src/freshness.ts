import type { TableCommitApiResponse } from "./api/types";

const HOUR_MS = 3_600_000;
const BUCKET_COUNT = 24;

export interface HourlyCommitBucket {
  hourStart: string;
  byOperation: Record<string, number>;
}

export function hourlyCommitBuckets(
  commits: TableCommitApiResponse[],
  now: Date,
): HourlyCommitBucket[] {
  const windowStart = now.getTime() - BUCKET_COUNT * HOUR_MS;
  const buckets: HourlyCommitBucket[] = Array.from({ length: BUCKET_COUNT }, (_, index) => ({
    hourStart: new Date(windowStart + index * HOUR_MS).toISOString(),
    byOperation: {},
  }));
  for (const commit of commits) {
    const offset = new Date(commit.committed_at).getTime() - windowStart;
    if (Number.isNaN(offset) || offset < 0 || offset >= BUCKET_COUNT * HOUR_MS) continue;
    const bucket = buckets[Math.floor(offset / HOUR_MS)];
    if (bucket === undefined) continue;
    const operation = commit.operation ?? "unknown";
    bucket.byOperation[operation] = (bucket.byOperation[operation] ?? 0) + 1;
  }
  return buckets;
}

export function writerMix(commits: TableCommitApiResponse[]): Record<string, number> {
  const mix: Record<string, number> = {};
  for (const commit of commits) {
    mix[commit.writer] = (mix[commit.writer] ?? 0) + 1;
  }
  return mix;
}
