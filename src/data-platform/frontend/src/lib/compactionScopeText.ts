import type { TableMaintenanceRunApiResponse, TableMaintenanceRunPartitionFieldApiResponse } from "@/api/generated/model";

export interface CompactionScope {
  summary: string;
  partitions: { specId: number; text: string }[];
}

// A field reads as its column for an identity transform, otherwise as the transform applied to it: `day(ts)`.
function fieldText({ column, transform }: TableMaintenanceRunPartitionFieldApiResponse): string {
  return transform === "identity" ? column : `${transform}(${column})`;
}

// What a compaction run compacted: the whole table, or the partitions over the target, each named by its
// fields' values within its partition spec. Only a compaction has a scope.
export function compactionScopeText(run: TableMaintenanceRunApiResponse): CompactionScope | null {
  if (run.operation !== "rewrite_data_files") return null;
  if (run.partitions.length === 0) return { summary: "Whole table", partitions: [] };
  return {
    summary: "Partitions over the target",
    partitions: run.partitions.flatMap((spec) =>
      spec.partitions.map((values) => ({
        specId: spec.spec_id,
        text: spec.fields.map((field, index) => `${fieldText(field)} = ${values[index] ?? "null"}`).join(", "),
      })),
    ),
  };
}
