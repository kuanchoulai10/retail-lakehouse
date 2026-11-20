import type { DiffChange } from "@retail-lakehouse/design-system";

type Retagged<K extends string> = Exclude<K, "added" | "removed">;

// How one compared field reads in a DiffList: added, removed, changed or unchanged, and a tag per change that is
// neither an addition nor a removal, in the order the API lists them.
export function diffChange<K extends string>(
  changes: readonly K[],
  tagOf: (change: Retagged<K>) => string,
): { change: DiffChange; tags: string[] } {
  if (changes.includes("added" as K)) return { change: "added", tags: [] };
  if (changes.includes("removed" as K)) return { change: "removed", tags: [] };
  const tags = changes.flatMap((kind) => (kind === "added" || kind === "removed" ? [] : [tagOf(kind as Retagged<K>)]));
  return { change: changes.length > 0 ? "changed" : "unchanged", tags };
}
