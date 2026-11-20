import type { SchemaChangeCountsApiResponse, SchemaFieldComparisonApiResponseChangesItem } from "@/api/generated/model";

type Retagged = Exclude<SchemaFieldComparisonApiResponseChangesItem, "added" | "removed">;

const TAGS: Record<Retagged, string> = {
  renamed: "Renamed",
  type_changed: "Type changed",
  nullability_changed: "Nullability changed",
  doc_changed: "Doc changed",
};

// Enum order, so a summary always reads the same way.
const PARTS: [keyof SchemaChangeCountsApiResponse, (count: number) => string][] = [
  ["added", (count) => `+${count} added`],
  ["removed", (count) => `−${count} removed`],
  ["renamed", (count) => `${count} renamed`],
  ["type_changed", (count) => `${count} type changed`],
  ["nullability_changed", (count) => `${count} nullability changed`],
  ["doc_changed", (count) => `${count} doc changed`],
];

// What a schema version changed against the one before it, in one line; null is the first version.
export function schemaChangeSummary(changes: SchemaChangeCountsApiResponse | null): string {
  if (changes === null) return "First version";
  const parts = PARTS.filter(([kind]) => changes[kind] > 0).map(([kind, text]) => text(changes[kind]));
  return parts.length === 0 ? "No changes" : parts.join(" · ");
}

export function schemaChangeTag(change: Retagged): string {
  return TAGS[change];
}
