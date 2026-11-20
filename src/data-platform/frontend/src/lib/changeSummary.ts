// One kind of change and how its count reads in a version's summary.
export type ChangeSummaryPart<K extends string> = readonly [K, (count: number) => string];

// What a version changed against the one before it, in one line, kinds in the order of `parts`; null is the first version.
export function changeSummary<K extends string>(
  parts: readonly ChangeSummaryPart<K>[],
  changes: Readonly<Record<K, number>> | null,
): string {
  if (changes === null) return "First version";
  const texts = parts.filter(([kind]) => changes[kind] > 0).map(([kind, text]) => text(changes[kind]));
  return texts.length === 0 ? "No changes" : texts.join(" · ");
}
