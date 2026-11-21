import { describe, expect, it } from "vitest";
import type { TableMaintenanceRunOperationApiResponse } from "@/api/generated/model";
import { compactionScopeText } from "./compactionScopeText";

function operation(overrides: Partial<TableMaintenanceRunOperationApiResponse>): TableMaintenanceRunOperationApiResponse {
  return {
    operation: "rewrite_data_files",
    status: "succeeded",
    attempts: 1,
    started_at: "2026-11-20T10:00:00Z",
    finished_at: "2026-11-20T10:05:00Z",
    job_name: "job-1",
    metrics: {},
    error: null,
    expected_files: null,
    filters: [],
    attempt_history: [],
    ...overrides,
  };
}

describe("compactionScopeText", () => {
  it("says nothing for an operation other than a compaction", () => {
    expect(compactionScopeText(operation({ operation: "expire_snapshots" }))).toBeNull();
  });

  it("says the whole table for a compaction with no filters", () => {
    expect(compactionScopeText(operation({ filters: [] }))).toEqual({ summary: "Whole table", wheres: [] });
  });

  it("lists the where clause of each partition spec in the API's order", () => {
    const scope = compactionScopeText(
      operation({
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
