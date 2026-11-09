import { describe, expect, it } from "vitest";
import type {
  ReconciliationMeasurementApiResponse,
  ReconciliationOperationApiResponse,
  TableReconciliationApiResponse,
} from "../../api/generated/model";
import { headline, reasonSentence, wakeText } from "./reconciliationText";

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
});

describe("reasonSentence", () => {
  it("started cites the met deciding measurements", () => {
    expect(reasonSentence(op({ result: "started", measurements: [REDUCIBLE_MET, context("target_file_size", 134217728, "bytes")] }))).toBe(
      "Because reducible files 1,240 (≥ 5).",
    );
  });

  it("words partition-scope compaction per partition, never comparing the sum with the threshold", () => {
    const measurements = [REDUCIBLE_MET, context("target_file_size", 134217728, "bytes"), context("qualifying_partitions", 3)];
    expect(reasonSentence(op({ result: "started", operation: "rewrite_data_files", measurements }))).toBe(
      "Because reducible files 1,240 across 3 partitions (≥ 5 per partition).",
    );
  });

  it("would start reads like started", () => {
    expect(reasonSentence(op({ result: "would_start", measurements: [REDUCIBLE_MET] }))).toBe("Because reducible files 1,240 (≥ 5).");
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
      "Due (reducible files 1,240 (≥ 5)), but the run could not be started.",
    );
  });

  it("not needed cites the unmet measurements", () => {
    expect(reasonSentence(op({ result: "not_needed" }))).toBe("Not yet: small manifests 12 (≥ 20).");
  });

  it("not needed with no qualifying partition says so per partition", () => {
    const measurements = [
      measurement({ key: "reducible_files", observed: 0, threshold: 5 }),
      context("qualifying_partitions", 0),
    ];
    expect(reasonSentence(op({ result: "not_needed", measurements }))).toBe(
      "Not yet: reducible files 0 across 0 partitions (≥ 5 per partition).",
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
    ).toBe("Due (expirable snapshots 312 (≥ 1)), but it ran recently; next allowed Nov 14, 03:00.");
  });

  it("cooling down below the threshold says not yet and when it is next allowed", () => {
    const at = new Date(2026, 10, 14, 3, 0).toISOString();
    expect(reasonSentence(op({ result: "cooling_down", next_eligible_at: at }))).toBe(
      "Not yet: small manifests 12 (≥ 20); next allowed Nov 14, 03:00.",
    );
  });

  it("cooling down with nothing measured only names the time", () => {
    const at = new Date(2026, 10, 14, 3, 0).toISOString();
    expect(reasonSentence(op({ result: "cooling_down", measurements: [], next_eligible_at: at }))).toBe(
      "Ran recently; next allowed Nov 14, 03:00.",
    );
  });

  it("off says it is turned off", () => {
    expect(reasonSentence(op({ result: "off", measurements: [] }))).toBe("Turned off in this table's settings.");
  });

  it("not checked says the manual run did not name it", () => {
    expect(reasonSentence(op({ result: "not_checked", measurements: [] }))).toBe("Not part of this manual run.");
  });

  it("formats bytes and seconds in their unit", () => {
    const m = measurement({ key: "small_manifests", observed: 2048, unit: "bytes", threshold: 1024, comparison: ">", met: true });
    expect(reasonSentence(op({ result: "started", measurements: [m] }))).toBe("Because small manifests 2.0 KB (> 1.0 KB).");
    const s = measurement({ key: "oldest_snapshot_age", observed: 7200, unit: "seconds", threshold: 3600, comparison: ">=", met: true });
    expect(reasonSentence(op({ result: "started", measurements: [s] }))).toBe("Because oldest snapshot age 2 h (≥ 1 h).");
  });
});
