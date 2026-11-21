import type { DiffListItem } from "@retail-lakehouse/design-system";
import type { TableDiscoveryPolicyVersionApiResponse } from "@/api/generated/model";
import { draftFromPolicy, outcomeLabel, ruleText, type DiscoveryRuleDraft } from "./discoveryPolicyDraft";

const NO_DESCRIPTION = "—";

function sameContent(a: DiscoveryRuleDraft, b: DiscoveryRuleDraft): boolean {
  return JSON.stringify([a.outcome, a.namespaces, a.tableNames]) === JSON.stringify([b.outcome, b.namespaces, b.tableNames]);
}

// The positions in `values` of one longest strictly increasing subsequence (patience sorting).
function longestIncreasing(values: number[]): Set<number> {
  const tails: number[] = [];
  const previous: number[] = [];
  values.forEach((value, index) => {
    let low = 0;
    let high = tails.length;
    while (low < high) {
      const middle = (low + high) >> 1;
      if (values[tails[middle]!]! < value) low = middle + 1;
      else high = middle;
    }
    previous[index] = low > 0 ? tails[low - 1]! : -1;
    tails[low] = index;
  });
  const kept = new Set<number>();
  for (let index = tails.at(-1) ?? -1; index !== -1; index = previous[index]!) kept.add(index);
  return kept;
}

// The rules kept by both versions that moved: the fewest that explain the new order. The kept rules
// in the new order are read as their old positions; those on one longest increasing run kept their
// place relative to each other, and only the others moved. A rule added or removed moves no one.
function movedRuleIds(before: DiscoveryRuleDraft[], after: DiscoveryRuleDraft[]): Set<string | null> {
  const oldPositions = new Map(before.map((rule, index) => [rule.id, index]));
  const kept = after.filter((rule) => oldPositions.has(rule.id));
  const stayed = longestIncreasing(kept.map((rule) => oldPositions.get(rule.id)!));
  return new Set(kept.filter((_rule, index) => !stayed.has(index)).map((rule) => rule.id));
}

// A move is told by where the rule now sits, never by numbers, which shift with every insert.
function moveText(after: DiscoveryRuleDraft[], index: number): string {
  const below = after[index + 1];
  return below === undefined ? "Moved to the end" : `Moved above ${ruleText(below)}`;
}

// What a kept version changed from the one before it, matched by rule id: each rule added, removed,
// changed (its outcome or a condition) or moved, then unchanged ones; and the description and the
// no-match outcome when they changed. A rule is named by its position, "Rule #2".
export function discoveryPolicyChanges(
  previous: TableDiscoveryPolicyVersionApiResponse,
  current: TableDiscoveryPolicyVersionApiResponse,
): DiffListItem[] {
  const before = draftFromPolicy(previous);
  const after = draftFromPolicy(current);
  const items: DiffListItem[] = [];

  if (before.description !== after.description) {
    items.push({
      id: "description",
      change: "changed",
      label: "Description",
      before: before.description || NO_DESCRIPTION,
      after: after.description || NO_DESCRIPTION,
    });
  }
  if (before.noMatchOutcome !== after.noMatchOutcome) {
    items.push({
      id: "no-match-outcome",
      change: "changed",
      label: "When no rule matches",
      before: outcomeLabel(before.noMatchOutcome),
      after: outcomeLabel(after.noMatchOutcome),
    });
  }

  const earlier = new Map(before.rules.map((rule) => [rule.id, rule]));
  const laterIds = new Set(after.rules.map((rule) => rule.id));
  const moved = movedRuleIds(before.rules, after.rules);

  after.rules.forEach((rule, index) => {
    const id = rule.id ?? rule.key;
    const label = `Rule #${index + 1}`;
    const old = earlier.get(rule.id);
    if (old === undefined) {
      items.push({ id, change: "added", label, after: ruleText(rule) });
      return;
    }
    const move = moved.has(rule.id) ? moveText(after.rules, index) : null;
    if (!sameContent(old, rule)) {
      items.push({
        id,
        change: "changed",
        label,
        ...(move === null ? {} : { tags: ["Changed", "Moved"] }),
        before: ruleText(old),
        after: ruleText(rule),
        ...(move === null ? {} : { description: move }),
      });
    } else if (move !== null) {
      items.push({ id, change: "changed", label, tags: ["Moved"], after: move });
    } else {
      items.push({ id, change: "unchanged", label, after: ruleText(rule) });
    }
  });

  before.rules.forEach((rule, index) => {
    if (laterIds.has(rule.id)) return;
    items.push({ id: rule.id ?? rule.key, change: "removed", label: `Rule #${index + 1}`, before: ruleText(rule) });
  });

  return items;
}
