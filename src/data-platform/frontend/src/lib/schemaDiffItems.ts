import type { DiffListItem } from "@retail-lakehouse/design-system";
import type { CatalogTableSchemaComparisonApiResponse, SchemaFieldComparisonApiResponse } from "@/api/generated/model";
import { diffChange } from "@/lib/diffChange";
import { schemaChangeTag } from "@/lib/schemaChangeText";

function typeAndRequirement(type: string | null, required: boolean | null): string | undefined {
  return type === null ? undefined : `${type} · ${required ? "required" : "optional"}`;
}

function descriptionOf(field: SchemaFieldComparisonApiResponse): string | undefined {
  const parts: string[] = [];
  if (field.changes.includes("renamed")) parts.push(`Renamed from ${(field.previous_path ?? []).join(".")}`);
  if (field.changes.includes("doc_changed")) {
    parts.push(`Doc: ${field.previous_doc ?? "none"} → ${field.doc ?? "none"}`);
  }
  if (parts.length > 0) return parts.join(" · ");
  return field.doc ?? undefined;
}

// One row per field, matched by field id: a renamed field is one row, never a removal and an addition.
export function schemaDiffItems(comparison: CatalogTableSchemaComparisonApiResponse): DiffListItem[] {
  return comparison.fields.map((field) => {
    const { change, tags } = diffChange(field.changes, schemaChangeTag);
    const changedValue = field.changes.includes("type_changed") || field.changes.includes("nullability_changed");
    return {
      id: String(field.field_id),
      change,
      label: (field.path ?? field.previous_path ?? []).join("."),
      depth: field.depth,
      tags,
      before:
        change === "removed" || changedValue
          ? typeAndRequirement(field.previous_type, field.previous_required)
          : undefined,
      after: change === "removed" ? undefined : typeAndRequirement(field.type, field.required),
      description: descriptionOf(field),
    };
  });
}
