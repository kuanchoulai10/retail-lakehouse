import { ApiError } from "@/api/apiError";
import type { ScannedCatalogApiResponse, TableApiResponse } from "@/api/generated/model";
import type { MaintenanceEmptyReason } from "@/components/MaintenanceEmptyState";
import { catalogScanState } from "@/lib/catalogScanState";

// Whether maintenance manages a catalog table, worked out from the catalogs discovery scans and
// maintenance's record for the table's uuid, in the spec's order: a catalog no discovery policy
// manages tables in first, then one discovery cannot read, then a missing record, then an
// unmanaged or dropped one.
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
  scanned: QueryResult<ScannedCatalogApiResponse[]>,
  maintenance: QueryResult<TableApiResponse>,
): TableMaintenanceState {
  if (scanned.isError) return { kind: "failed", error: scanned.error };
  if (scanned.data === undefined) return { kind: "loading" };
  const scan = catalogScanState(catalog, scanned.data);
  if (scan.kind === "not-scanned") return { kind: "unmanaged", reason: "catalog-not-scanned" };
  if (scan.kind === "failed" && scan.reason === "cannot_access") {
    return { kind: "unmanaged", reason: "catalog-cannot-access" };
  }
  if (maintenance.isError) {
    if (maintenance.error instanceof ApiError && maintenance.error.status === 404) {
      return { kind: "unmanaged", reason: "not-found" };
    }
    return { kind: "failed", error: maintenance.error };
  }
  if (maintenance.data === undefined) return { kind: "loading" };
  const status = maintenance.data.status.toLowerCase();
  if (status === "unmanaged" || status === "dropped") return { kind: "unmanaged", reason: status };
  return { kind: "managed", table: maintenance.data };
}
