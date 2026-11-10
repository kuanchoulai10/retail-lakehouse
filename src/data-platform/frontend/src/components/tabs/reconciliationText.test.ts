import { describe, expect, it } from "vitest";
import type {
  ReconciliationMeasurementApiResponse,
  ReconciliationOperationApiResponse,
  TableReconciliationApiResponse,
} from "../../api/generated/model";
import { foldText, headline, reasonSentence, wakeText } from "./reconciliationText";

function measurement(overrides: Partial<ReconciliationMeasurementApiResponse>): ReconciliationMeasurementApiResponse {
  return { key: "small_manifests", observed: 12, unit: "count", threshold: 20, comparison: ">=", met: false, ...overrides };
}

function context(key: string, observed: number, unit = "count"): ReconciliationMeasurementApiResponse {
  return { key, observed, unit, threshold: null, comparison: null, met: null };
}

function op(overrides: Partial<ReconciliationOperationApiResponse>): ReconciliationOperationApiResponse {
  return {
    operation: "rewrite_manifests",
    result: "not_needed",
    combine: "all",
    measurements: [measurement({})],
    next_eligible_at: null,
    ...overrides,
  };
}

function record(overrides: Partial<TableReconciliationApiResponse>): TableReconciliationApiResponse {
  return {
    reconciliation_id: "rec-1",
    table_uuid: "uuid-orders",
    reconciled_at: "2026-11-10T10:42:00Z",
    wake_reasons: { schedule: 1 },
    dry_run: false,
    outcome: "planned",
    skip_reason: null,
    operations: [],
    run_id: null,
    ...overrides,
  };
}

const REDUCIBLE_MET = measurement({ key: "reducible_files", observed: 1240, threshold: 5, met: true });

describe("headline", () => {
  it("names the operations a reconciliation started", () => {
    const r = record({
      run_id: "run-42",
      operations: [op({ operation: "rewrite_data_files", result: "started" }), op({ operation: "expire_snapshots", result: "started" })],
    });
    expect(headline(r)).toBe("Started Rewrite data files, Expire snapshots");
  });

  it("says would start in dry run", () => {
    const r = record({ dry_run: true, operations: [op({ operation: "rewrite_data_files", result: "would_start" })] });
    expect(headline(r)).toBe("Would start Rewrite data files");
  });

  it("says so when a start failed", () => {
    const r = record({ operations: [op({ operation: "rewrite_data_files", result: "start_failed" })] });
    expect(headline(r)).toBe("Could not start Rewrite data files");
  });

  it("is nothing to do when nothing was due", () => {
    expect(headline(record({ operations: [op({})] }))).toBe("Nothing to do");
  });

  it("names the skip reason", () => {
    expect(headline(record({ outcome: "skipped", skip_reason: "paused" }))).toBe("Skipped: table paused");
    expect(headline(record({ outcome: "skipped", skip_reason: "not_found" }))).toBe("Skipped: table not found");
  });

  it("explains a manual run in dry run, so started and dry run do not read as a contradiction", () => {
    const r = record({
      dry_run: true,
      wake_reasons: { manual_run: 1 },
      run_id: "run-43",
      operations: [op({ operation: "remove_orphan_files", result: "started", measurements: [] })],
    });
    expect(headline(r)).toBe("Started Remove orphan files (manual run, dry run is on)");
  });
});

describe("wakeText", () => {
  it("puts the most frequent reason first, with counts above one", () => {
    expect(wakeText(record({ wake_reasons: { schedule: 1, catalog_commit: 3 } }))).toBe("Catalog commit × 3, Schedule");
  });

  it("breaks ties in the order the reasons are defined", () => {
    expect(wakeText(record({ wake_reasons: { previous_run_finished: 1, settings_changed: 1, schedule: 1 } }))).toBe(
      "Schedule, Settings changed, Previous run finished",
    );
  });

  it("names a discovery scan and ranks it right after a catalog commit", () => {
    expect(wakeText(record({ wake_reasons: { settings_changed: 1, discovery_scan: 1, catalog_commit: 1 } }))).toBe(
      "Catalog commit, Discovery scan, Settings changed",
    );
  });
});

describe("reasonSentence", () => {
  it("started cites the met deciding measurements", () => {
    expect(reasonSentence(op({ result: "started", measurements: [REDUCIBLE_MET, context("target_file_size", 134217728, "bytes")] }))).toBe(
      "Because reducible files 1,240 (needs ≥ 5).",
    );
  });

  it("words partition-scope compaction per partition, never comparing the sum with the threshold", () => {
    const measurements = [REDUCIBLE_MET, context("target_file_size", 134217728, "bytes"), context("qualifying_partitions", 3)];
    expect(reasonSentence(op({ result: "started", operation: "rewrite_data_files", measurements }))).toBe(
      "Because reducible files 1,240 across 3 partitions (needs ≥ 5 per partition).",
    );
  });

  it("would start reads like started", () => {
    expect(reasonSentence(op({ result: "would_start", measurements: [REDUCIBLE_MET] }))).toBe("Because reducible files 1,240 (needs ≥ 5).");
  });

  it("an operation with nothing to measure is due whenever its cooldown allows", () => {
    expect(reasonSentence(op({ result: "started", operation: "remove_orphan_files", measurements: [] }))).toBe(
      "Due whenever its cooldown allows.",
    );
  });

  it("a manual run started what the user named", () => {
    expect(reasonSentence(op({ result: "started", measurements: [] }), { manualRun: true })).toBe("Asked for in a manual run.");
  });

  it("start failed says it was due but could not start", () => {
    expect(reasonSentence(op({ result: "start_failed", measurements: [REDUCIBLE_MET] }))).toBe(
      "Due: reducible files 1,240 (needs ≥ 5), but the run could not be started.",
    );
  });

  it("not needed cites the unmet measurements", () => {
    expect(reasonSentence(op({ result: "not_needed" }))).toBe("Not yet: small manifests 12 (needs ≥ 20).");
  });

  it("not needed with no qualifying partition says so per partition", () => {
    const measurements = [
      measurement({ key: "reducible_files", observed: 0, threshold: 5 }),
      context("qualifying_partitions", 0),
    ];
    expect(reasonSentence(op({ result: "not_needed", measurements }))).toBe(
      "Not yet: reducible files 0 across 0 partitions (needs ≥ 5 per partition).",
    );
  });

  it("cooling down names when it is next allowed", () => {
    const at = new Date(2026, 10, 14, 3, 0).toISOString();
    expect(
      reasonSentence(
        op({
          result: "cooling_down",
          measurements: [measurement({ key: "expirable_snapshots", observed: 312, threshold: 1, met: true })],
          next_eligible_at: at,
        }),
      ),
    ).toBe("Due: expirable snapshots 312 (needs ≥ 1), but it ran recently; next allowed Nov 14, 03:00.");
  });

  it("cooling down below the threshold says not yet and when it is next allowed", () => {
    const at = new Date(2026, 10, 14, 3, 0).toISOString();
    expect(reasonSentence(op({ result: "cooling_down", next_eligible_at: at }))).toBe(
      "Not yet: small manifests 12 (needs ≥ 20); next allowed Nov 14, 03:00.",
    );
  });

  it("cooling down with any combine and a met measurement says it was due", () => {
    const at = new Date(2026, 10, 14, 3, 0).toISOString();
    const measurements = [
      measurement({ key: "small_manifests", observed: 42, threshold: 20, met: true }),
      measurement({ key: "manifests_per_snapshot", observed: 61, threshold: 100, comparison: ">", met: false }),
    ];
    expect(reasonSentence(op({ result: "cooling_down", combine: "any", measurements, next_eligible_at: at }))).toBe(
      "Due: small manifests 42 (needs ≥ 20), but it ran recently; next allowed Nov 14, 03:00.",
    );
  });

  it("not needed with any combine cites every deciding measurement", () => {
    const measurements = [
      measurement({ key: "small_manifests", observed: 12, threshold: 20, met: false }),
      measurement({ key: "manifests_per_snapshot", observed: 61, threshold: 100, comparison: ">", met: false }),
    ];
    expect(reasonSentence(op({ result: "not_needed", combine: "any", measurements }))).toBe(
      "Not yet: small manifests 12 (needs ≥ 20) and manifests per snapshot 61 (needs > 100).",
    );
  });

  it("cooling down with nothing measured only names the time", () => {
    const at = new Date(2026, 10, 14, 3, 0).toISOString();
    expect(reasonSentence(op({ result: "cooling_down", measurements: [], next_eligible_at: at }))).toBe(
      "Ran recently; next allowed Nov 14, 03:00.",
    );
  });

  it("not needed reads the threshold as what it needs", () => {
    const m = measurement({ key: "expirable_snapshots", observed: 0, threshold: 1, met: false });
    expect(reasonSentence(op({ result: "not_needed", operation: "expire_snapshots", measurements: [m] }))).toBe(
      "Not yet: expirable snapshots 0 (needs ≥ 1).",
    );
  });

  it("cooling down in partition scope never nests parentheses", () => {
    const at = new Date(2026, 10, 14, 3, 0).toISOString();
    const measurements = [
      measurement({ key: "reducible_files", observed: 15, threshold: 2, met: true }),
      context("qualifying_partitions", 2),
    ];
    const sentence = reasonSentence(
      op({ result: "cooling_down", operation: "rewrite_data_files", measurements, next_eligible_at: at }),
    );
    expect(sentence).toBe(
      "Due: reducible files 15 across 2 partitions (needs ≥ 2 per partition), but it ran recently; next allowed Nov 14, 03:00.",
    );
    expect(sentence).not.toMatch(/\([^)]*\(/);
  });

  it("start failed in partition scope never nests parentheses", () => {
    const measurements = [REDUCIBLE_MET, context("qualifying_partitions", 3)];
    const sentence = reasonSentence(op({ result: "start_failed", operation: "rewrite_data_files", measurements }));
    expect(sentence).toBe("Due: reducible files 1,240 across 3 partitions (needs ≥ 5 per partition), but the run could not be started.");
    expect(sentence).not.toMatch(/\([^)]*\(/);
  });

  it("off says it is turned off", () => {
    expect(reasonSentence(op({ result: "off", measurements: [] }))).toBe("Turned off in this table's settings.");
  });

  it("not checked says the manual run did not name it", () => {
    expect(reasonSentence(op({ result: "not_checked", measurements: [] }))).toBe("Not part of this manual run.");
  });

  it("formats bytes and seconds in their unit", () => {
    const m = measurement({ key: "small_manifests", observed: 2048, unit: "bytes", threshold: 1024, comparison: ">", met: true });
    expect(reasonSentence(op({ result: "started", measurements: [m] }))).toBe("Because small manifests 2.0 KB (needs > 1.0 KB).");
    const s = measurement({ key: "oldest_snapshot_age", observed: 7200, unit: "seconds", threshold: 3600, comparison: ">=", met: true });
    expect(reasonSentence(op({ result: "started", measurements: [s] }))).toBe("Because oldest snapshot age 2 h (needs ≥ 1 h).");
  });
});

describe("foldText", () => {
  const local = (hour: number) => new Date(2026, 10, 10, hour, 42).toISOString();

  it("names a quiet stretch by its first and last time", () => {
    const records = [record({ reconciled_at: local(4) }), record({ reconciled_at: local(3) })];
    expect(foldText(records)).toBe("2 reconciliations found nothing to do, 03:42–04:42");
  });

  it("names a stretch of skips by the skip reason", () => {
    const records = [4, 3, 2].map((hour) =>
      record({ reconciled_at: local(hour), outcome: "skipped", skip_reason: "paused", wake_reasons: { schedule: 1 } }),
    );
    expect(foldText(records)).toBe("3 reconciliations skipped: table paused, 02:42–04:42");
  });
});
