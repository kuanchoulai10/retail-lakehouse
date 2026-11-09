import { describe, expect, it } from "vitest";
import type { TableCommitApiResponse } from "./api/generated/model";
import { hourlyCommitBuckets, writerMix } from "./freshness";

const NOW = new Date("2026-10-31T10:20:00Z");

function commit(minutesAgo: number, overrides: Partial<TableCommitApiResponse> = {}) {
  return {
    snapshot_id: String(minutesAgo),
    parent_id: null,
    committed_at: new Date(NOW.getTime() - minutesAgo * 60_000).toISOString(),
    operation: "append",
    writer: "kafka_connect",
    added_records: null,
    deleted_records: null,
    added_data_files: null,
    deleted_data_files: null,
    added_delete_files: null,
    removed_delete_files: null,
    summary: {},
    ...overrides,
  } satisfies TableCommitApiResponse;
}

describe("hourlyCommitBuckets", () => {
  it("returns 24 buckets, oldest first, ending at now", () => {
    const buckets = hourlyCommitBuckets([], NOW);
    expect(buckets).toHaveLength(24);
    expect(buckets[23]?.hourStart).toBe("2026-10-31T09:20:00.000Z");
    expect(buckets[0]?.hourStart).toBe("2026-10-30T10:20:00.000Z");
  });

  it("counts commits at now-30m and now-90m in the last two buckets", () => {
    const buckets = hourlyCommitBuckets(
      [commit(30), commit(90, { operation: "overwrite" })],
      NOW,
    );
    expect(buckets[23]?.byOperation).toEqual({ append: 1 });
    expect(buckets[22]?.byOperation).toEqual({ overwrite: 1 });
    expect(buckets.slice(0, 22).every((b) => Object.keys(b.byOperation).length === 0)).toBe(true);
  });

  it("ignores commits outside the 24 hour window and labels a missing operation unknown", () => {
    const buckets = hourlyCommitBuckets([commit(25 * 60), commit(10, { operation: null })], NOW);
    expect(buckets[23]?.byOperation).toEqual({ unknown: 1 });
    expect(buckets.flatMap((b) => Object.values(b.byOperation))).toEqual([1]);
  });
});

describe("writerMix", () => {
  it("counts commits per writer", () => {
    const mix = writerMix([
      commit(1),
      commit(2),
      commit(3, { writer: "spark" }),
      commit(4, { writer: "unknown" }),
    ]);
    expect(mix).toEqual({ kafka_connect: 2, spark: 1, unknown: 1 });
  });
});
