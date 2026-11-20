import type { DiffListItem } from "@retail-lakehouse/design-system";
import type { CatalogTablePartitionSpecComparisonApiResponse } from "@/api/generated/model";
import { diffChange } from "@/lib/diffChange";
import { partitionChangeTag } from "@/lib/partitionChangeText";

// One row per partition field; a field whose transform changed is one row reading `before → after`.
export function partitionDiffItems(comparison: CatalogTablePartitionSpecComparisonApiResponse): DiffListItem[] {
  return comparison.fields.map((field) => {
    const { change, tags } = diffChange(field.changes, partitionChangeTag);
    return {
      id: String(field.field_id ?? field.previous_field_id),
      change,
      label: field.name ?? field.previous_name ?? "",
      tags,
      before:
        change === "removed" || field.changes.includes("transform_changed")
          ? (field.previous_expression ?? undefined)
          : undefined,
      after: field.expression ?? undefined,
      description: field.changes.includes("renamed") ? `Renamed from ${field.previous_name}` : undefined,
    };
  });
}
