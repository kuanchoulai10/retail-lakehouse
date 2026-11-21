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
    filters: [],
    procedure_args: {},
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

  it("says the whole table for a compaction with no filters", () => {
    expect(compactionScopeText(run({ filters: [] }))).toEqual({ summary: "Whole table", wheres: [] });
  });

  it("names the partitions over the target for a compaction with exactly one filter", () => {
    expect(compactionScopeText(run({ filters: [{ spec_id: 0, where: "(`region` = 'eu')" }] }))).toEqual({
      summary: "Partitions over the target",
      wheres: [{ specId: 0, where: "(`region` = 'eu')" }],
    });
  });

  it("lists the where clause of each partition spec in the API's order", () => {
    const scope = compactionScopeText(
      run({
        filters: [
          { spec_id: 0, where: "(`region` = 'eu')" },
          { spec_id: 1, where: "(`day` = DATE '2026-11-19')" },
        ],
      }),
    );
    expect(scope).toEqual({
      summary: "Partitions over the target",
      wheres: [
        { specId: 0, where: "(`region` = 'eu')" },
        { specId: 1, where: "(`day` = DATE '2026-11-19')" },
      ],
    });
  });
});
