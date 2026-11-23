import { describe, expect, it } from "vitest";
import type { TableMaintenanceRunApiResponse } from "@/api/generated/model";
import { compactionScopeText } from "./compactionScopeText";

function run(overrides: Partial<TableMaintenanceRunApiResponse>): TableMaintenanceRunApiResponse {
  return {
    run_id: "mr-1",
    table_uuid: "uuid-orders",
    execution_ref: "table-maintenance:table-uuid=uuid-orders",
    trigger: "scheduled",
    operation: "rewrite_data_files",
    priority: "P3",
    status: "succeeded",
    created_at: "2026-11-20T10:00:00Z",
    started_at: "2026-11-20T10:00:00Z",
    finished_at: "2026-11-20T10:05:00Z",
    settings: {},
    partitions: [],
    metrics: {},
    error: null,
    skip_reason: null,
    attempts: [],
    ...overrides,
  };
}

describe("compactionScopeText", () => {
  it("says nothing for a run of an operation other than a compaction", () => {
    expect(compactionScopeText(run({ operation: "expire_snapshots" }))).toBeNull();
  });

  it("says the whole table for a compaction with no partitions", () => {
    expect(compactionScopeText(run({ partitions: [] }))).toEqual({ summary: "Whole table", partitions: [] });
  });

  it("names each partition by its columns and values, an identity field by its column alone", () => {
    const scope = compactionScopeText(
      run({
        partitions: [
          {
            spec_id: 0,
            fields: [
              { column: "region", transform: "identity" },
              { column: "ts", transform: "day" },
            ],
            partitions: [
              ["eu", "2026-11-19"],
              ["us", null],
            ],
          },
        ],
      }),
    );
    expect(scope).toEqual({
      summary: "Partitions over the target",
      partitions: [
        { specId: 0, text: "region = eu, day(ts) = 2026-11-19" },
        { specId: 0, text: "region = us, day(ts) = null" },
      ],
    });
  });

  it("lists the partitions of each partition spec in the API's order", () => {
    const scope = compactionScopeText(
      run({
        partitions: [
          { spec_id: 0, fields: [{ column: "region", transform: "identity" }], partitions: [["eu"]] },
          { spec_id: 1, fields: [{ column: "id", transform: "bucket[16]" }], partitions: [["3"]] },
        ],
      }),
    );
    expect(scope?.partitions).toEqual([
      { specId: 0, text: "region = eu" },
      { specId: 1, text: "bucket[16](id) = 3" },
    ]);
  });
});
