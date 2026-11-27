import { describe, expect, it } from "vitest";
import { ApiError } from "@/api/apiError";
import type { ScannedCatalogApiResponse, TableApiResponse } from "@/api/generated/model";
import { tableFixture } from "@/test/fixtures";
import { tableMaintenanceState } from "./tableMaintenanceState";

function loaded<T>(data: T) {
  return { data, error: null, isError: false };
}

function failed(error: unknown) {
  return { data: undefined, error, isError: true };
}

const PENDING = { data: undefined, error: null, isError: false };

function scanned(failure: ScannedCatalogApiResponse["failure"] = null): ScannedCatalogApiResponse {
  return { catalog: "iceberg", last_discovered_at: "2026-11-09T08:10:00Z", failure };
}

function failure(reason: "cannot_access" | "not_found"): ScannedCatalogApiResponse["failure"] {
  return { reason, detail: `${reason} detail`, failed_at: "2026-11-09T09:00:00Z" };
}

const MANAGED: TableApiResponse = tableFixture();

describe("tableMaintenanceState", () => {
  it("is loading until the scanned catalogs are read", () => {
    expect(tableMaintenanceState("iceberg", PENDING, loaded(MANAGED))).toEqual({ kind: "loading" });
  });

  it("fails when the scanned catalogs cannot be read", () => {
    const error = new Error("down");
    expect(tableMaintenanceState("iceberg", failed(error), loaded(MANAGED))).toEqual({ kind: "failed", error });
  });

  it("names a catalog discovery does not scan before reading the record", () => {
    const other = { ...scanned(), catalog: "other" };
    expect(tableMaintenanceState("iceberg", loaded([other]), loaded(MANAGED))).toEqual({
      kind: "unmanaged",
      reason: "catalog-not-scanned",
    });
  });

  it("names a scanned catalog discovery cannot read, before the record", () => {
    expect(tableMaintenanceState("iceberg", loaded([scanned(failure("cannot_access"))]), loaded(MANAGED))).toEqual({
      kind: "unmanaged",
      reason: "catalog-cannot-access",
    });
  });

  it("reads the record of a scanned catalog whose failure is not a refusal", () => {
    expect(tableMaintenanceState("iceberg", loaded([scanned(failure("not_found"))]), loaded(MANAGED))).toEqual({
      kind: "managed",
      table: MANAGED,
    });
  });

  it("reads a scanned catalog's record: missing, undecided, unmanaged, dropped or managed", () => {
    const catalogs = loaded([scanned()]);
    const missing = failed(new ApiError(404, "table uuid-orders not found"));
    expect(tableMaintenanceState("iceberg", catalogs, missing)).toEqual({ kind: "unmanaged", reason: "not-found" });
    for (const status of ["undecided", "unmanaged", "dropped"] as const) {
      expect(tableMaintenanceState("iceberg", catalogs, loaded(tableFixture({ status })))).toEqual({
        kind: "unmanaged",
        reason: status,
      });
    }
    expect(tableMaintenanceState("iceberg", catalogs, loaded(MANAGED))).toEqual({ kind: "managed", table: MANAGED });
  });
});

describe("tableMaintenanceState for an undecided table", () => {
  it("names a catalog discovery cannot read before an undecided record, since that is why it stays undecided", () => {
    const undecided = loaded(tableFixture({ status: "undecided", decided_by: null }));
    expect(tableMaintenanceState("iceberg", loaded([scanned(failure("cannot_access"))]), undecided)).toEqual({
      kind: "unmanaged",
      reason: "catalog-cannot-access",
    });
  });

  it("reads the status case-insensitively", () => {
    const undecided = loaded(tableFixture({ status: "UNDECIDED", decided_by: null }));
    expect(tableMaintenanceState("iceberg", loaded([scanned()]), undecided)).toEqual({
      kind: "unmanaged",
      reason: "undecided",
    });
  });
});
