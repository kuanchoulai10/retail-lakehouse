// The catalog, namespace or table a page shows, as a policy target.
export type PolicyScope =
  | { type: "catalog"; catalog: string }
  | { type: "namespace"; catalog: string; namespace: string[] }
  | { type: "table"; catalog: string; namespace: string[]; table: string; tableUuid: string };

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
