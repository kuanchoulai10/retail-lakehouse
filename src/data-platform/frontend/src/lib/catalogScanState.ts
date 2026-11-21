import type {
  CatalogScanFailureApiResponseReason,
  ScannedCatalogApiResponse,
} from "@/api/generated/model";

// Where discovery stands with one catalog, from `GET /v1/scanned-catalogs`: a catalog is scanned
// only while a policy that can manage tables is attached in it, and its failure is the current one.
export type CatalogScanState =
  | { kind: "scanned"; at: string }
  | { kind: "not-scanned-yet" }
  | { kind: "not-scanned" }
  | { kind: "failed"; reason: CatalogScanFailureApiResponseReason; detail: string };

const FAILURE_LABELS: Record<CatalogScanFailureApiResponseReason, string> = {
  cannot_access: "Cannot access",
  not_found: "Catalog not found",
};

// What a catalog's current scan failure means, in the words the list's banners and the
// attachment rows share.
export function scanFailureLabel(reason: CatalogScanFailureApiResponseReason): string {
  return FAILURE_LABELS[reason];
}

export function catalogScanState(catalog: string, scanned: ScannedCatalogApiResponse[]): CatalogScanState {
  const found = scanned.find((entry) => entry.catalog === catalog);
  if (found === undefined) return { kind: "not-scanned" };
  if (found.failure !== null) return { kind: "failed", reason: found.failure.reason, detail: found.failure.detail };
  if (found.last_discovered_at === null) return { kind: "not-scanned-yet" };
  return { kind: "scanned", at: found.last_discovered_at };
}
