import { describe, expect, it } from "vitest";
import type { TableMaintenanceRunApiResponse } from "@/api/generated/model";
import { anyRunInFlight } from "./anyRunInFlight";

function run(status: string, attemptStatuses: string[] = []): TableMaintenanceRunApiResponse {
  return {
    run_id: "mr-1",
    table_uuid: "uuid-orders",
    execution_ref: "table-maintenance:table-uuid=uuid-orders",
    trigger: "manual",
    operation: "rewrite_data_files",
    priority: "P3",
    status,
    created_at: "2026-11-20T10:00:00Z",
    started_at: attemptStatuses.length === 0 ? null : "2026-11-20T10:00:00Z",
    finished_at: null,
    settings: {},
    partitions: [],
    metrics: {},
    error: null,
    skip_reason: null,
    attempts: attemptStatuses.map((attemptStatus, index) => ({
      attempt: index + 1,
      size: "S",
      status: attemptStatus,
      started_at: "2026-11-20T10:00:00Z",
      started_running_at: null,
      finished_at: null,
      failure_class: null,
      error: null,
      event_log_finished: null,
      next_step: null,
      next_size: null,
      job_name: `job-${index + 1}`,
    })),
  };
}

describe("anyRunInFlight", () => {
  it.each(["pending", "queued", "running"])("is true for a %s run", (status) => {
    expect(anyRunInFlight([run("succeeded"), run(status)])).toBe(true);
  });

  it("is true for a pending run that has no attempt yet", () => {
    expect(anyRunInFlight([run("succeeded", ["succeeded"]), run("pending")])).toBe(true);
  });

  it("is false for a skipped run", () => {
    expect(anyRunInFlight([run("skipped")])).toBe(false);
  });

  it.each(["pending", "queued", "running"])("is true for a finished run with a %s attempt", (status) => {
    expect(anyRunInFlight([run("failed", ["failed", status])])).toBe(true);
  });

  it("is false when every run and attempt has ended", () => {
    expect(anyRunInFlight([run("succeeded", ["succeeded"]), run("failed", ["failed", "failed"])])).toBe(false);
  });

  it("is false before any runs are read", () => {
    expect(anyRunInFlight(undefined)).toBe(false);
    expect(anyRunInFlight([])).toBe(false);
  });
});
