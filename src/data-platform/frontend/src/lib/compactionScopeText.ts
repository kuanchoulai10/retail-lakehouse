import type { TableMaintenanceRunOperationApiResponse } from "@/api/generated/model";

export interface CompactionScope {
  summary: string;
  wheres: { specId: number; where: string }[];
}

// What a compaction compacted: the whole table, or the partitions over the target, which each spec's where clause names.
// Only a compaction has a scope.
export function compactionScopeText(operation: TableMaintenanceRunOperationApiResponse): CompactionScope | null {
  if (operation.operation !== "rewrite_data_files") return null;
  if (operation.filters.length === 0) return { summary: "Whole table", wheres: [] };
  return {
    summary: "Partitions over the target",
    wheres: operation.filters.map((filter) => ({ specId: filter.spec_id, where: filter.where })),
  };
}
