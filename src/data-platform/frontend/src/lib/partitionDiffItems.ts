import type { DiffChange, DiffListItem } from "@retail-lakehouse/design-system";
import type {
  CatalogTablePartitionSpecComparisonApiResponse,
  PartitionFieldComparisonApiResponse,
} from "@/api/generated/model";
import { partitionChangeTag } from "@/lib/partitionChangeText";

function changeOf(field: PartitionFieldComparisonApiResponse): DiffChange {
  if (field.changes.includes("added")) return "added";
  if (field.changes.includes("removed")) return "removed";
  return field.changes.length > 0 ? "changed" : "unchanged";
}

// One row per partition field; a field whose transform changed is one row reading `before → after`.
export function partitionDiffItems(comparison: CatalogTablePartitionSpecComparisonApiResponse): DiffListItem[] {
  return comparison.fields.map((field) => {
    const change = changeOf(field);
    return {
      id: String(field.field_id ?? field.previous_field_id),
      change,
      label: field.name ?? field.previous_name ?? "",
      tags: field.changes.flatMap((kind) => (kind === "added" || kind === "removed" ? [] : [partitionChangeTag(kind)])),
      before:
        change === "removed" || field.changes.includes("transform_changed")
          ? (field.previous_expression ?? undefined)
          : undefined,
      after: field.expression ?? undefined,
      description: field.changes.includes("renamed") ? `Renamed from ${field.previous_name}` : undefined,
    };
  });
}
