import type {
  PartitionChangeCountsApiResponse,
  PartitionFieldComparisonApiResponseChangesItem,
} from "@/api/generated/model";

type Retagged = Exclude<PartitionFieldComparisonApiResponseChangesItem, "added" | "removed">;

const TAGS: Record<Retagged, string> = {
  renamed: "Renamed",
  transform_changed: "Transform changed",
};

const PARTS: [keyof PartitionChangeCountsApiResponse, (count: number) => string][] = [
  ["added", (count) => `+${count} added`],
  ["removed", (count) => `−${count} removed`],
  ["renamed", (count) => `${count} renamed`],
  ["transform_changed", (count) => `${count} transform changed`],
];

// What a partition spec version changed against the one before it, in one line; null is the first version.
export function partitionChangeSummary(changes: PartitionChangeCountsApiResponse | null): string {
  if (changes === null) return "First version";
  const parts = PARTS.filter(([kind]) => changes[kind] > 0).map(([kind, text]) => text(changes[kind]));
  return parts.length === 0 ? "No changes" : parts.join(" · ");
}

export function partitionChangeTag(change: Retagged): string {
  return TAGS[change];
}
