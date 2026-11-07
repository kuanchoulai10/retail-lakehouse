import { ApiError } from "@/api/client";
import type { TableApiResponse } from "@/api/types";
import type { MaintenanceEmptyReason } from "@/components/MaintenanceEmptyState";

// Whether maintenance manages a catalog table, worked out from the catalogs maintenance covers
// and maintenance's record for the table's uuid, in the spec's order: an uncovered catalog
// first, then a missing record, then an excluded or dropped one. Active or paused is managed.
export type TableMaintenanceState =
  | { kind: "loading" }
  | { kind: "failed"; error: unknown }
  | { kind: "unmanaged"; reason: MaintenanceEmptyReason }
  | { kind: "managed"; table: TableApiResponse };

interface QueryResult<T> {
  data: T | undefined;
  error: unknown;
  isError: boolean;
}

export function tableMaintenanceState(
  catalog: string,
  covered: QueryResult<string[]>,
  maintenance: QueryResult<TableApiResponse>,
): TableMaintenanceState {
  if (covered.isError) return { kind: "failed", error: covered.error };
  if (covered.data === undefined) return { kind: "loading" };
  if (!covered.data.includes(catalog)) return { kind: "unmanaged", reason: "catalog-not-covered" };
  if (maintenance.isError) {
    if (maintenance.error instanceof ApiError && maintenance.error.status === 404) {
      return { kind: "unmanaged", reason: "not-found" };
    }
    return { kind: "failed", error: maintenance.error };
  }
  if (maintenance.data === undefined) return { kind: "loading" };
  const status = maintenance.data.status.toLowerCase();
  if (status === "excluded" || status === "dropped") return { kind: "unmanaged", reason: status };
  return { kind: "managed", table: maintenance.data };
}
