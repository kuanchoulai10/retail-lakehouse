import type {
  PartitionChangeCountsApiResponse,
  PartitionFieldComparisonApiResponseChangesItem,
} from "@/api/generated/model";
import { changeSummary, type ChangeSummaryPart } from "@/lib/changeSummary";

type Retagged = Exclude<PartitionFieldComparisonApiResponseChangesItem, "added" | "removed">;

const TAGS: Record<Retagged, string> = {
  renamed: "Renamed",
  transform_changed: "Transform changed",
};

// Enum order, so a summary always reads the same way.
const PARTS: ChangeSummaryPart<keyof PartitionChangeCountsApiResponse>[] = [
  ["added", (count) => `+${count} added`],
  ["removed", (count) => `−${count} removed`],
  ["renamed", (count) => `${count} renamed`],
  ["transform_changed", (count) => `${count} transform changed`],
];

// What a partition spec version changed against the one before it, in one line; null is the first version.
export function partitionChangeSummary(changes: PartitionChangeCountsApiResponse | null): string {
  return changeSummary(PARTS, changes);
}

export function partitionChangeTag(change: Retagged): string {
  return TAGS[change];
}
