// The catalog, namespace or table a page shows, as a policy target. A table is `recorded` when
// table maintenance has a record of it (its policy is then read by uuid, else by name).
export type PolicyScope =
  | { type: "catalog"; catalog: string }
  | { type: "namespace"; catalog: string; namespace: string[] }
  | { type: "table"; catalog: string; namespace: string[]; table: string; tableUuid: string; recorded: boolean };

// The target path the API takes: the catalog, the namespace levels, then the table name.
export function scopePath(scope: PolicyScope): string[] {
  switch (scope.type) {
    case "catalog":
      return [scope.catalog];
    case "namespace":
      return [scope.catalog, ...scope.namespace];
    case "table":
      return [scope.catalog, ...scope.namespace, scope.table];
  }
}
