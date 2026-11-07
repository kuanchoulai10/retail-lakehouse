// Query keys of the catalog API. A write invalidates the keys it affects, so the page
// refetches what Polaris holds instead of patching its cache.
export const catalogQueryKeys = {
  catalogs: () => ["catalogs"] as const,
  catalog: (catalog: string) => ["catalog", catalog] as const,
  // Prefix of every namespace listing in a catalog, at any level.
  namespaceLists: (catalog: string) => ["namespaces", catalog] as const,
  namespaces: (catalog: string, parent: string[]) => ["namespaces", catalog, parent] as const,
  namespace: (catalog: string, namespace: string[]) => ["namespace", catalog, namespace] as const,
  tables: (catalog: string, namespace: string[]) => ["catalog-tables", catalog, namespace] as const,
  views: (catalog: string, namespace: string[]) => ["views", catalog, namespace] as const,
  genericTables: (catalog: string, namespace: string[]) =>
    ["generic-tables", catalog, namespace] as const,
};
