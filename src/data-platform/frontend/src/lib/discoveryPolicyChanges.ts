import type { DiffListItem } from "@retail-lakehouse/design-system";
import type { TableDiscoveryPolicyVersionApiResponse } from "@/api/generated/model";
import { draftFromPolicy, outcomeLabel, ruleText, type DiscoveryRuleDraft } from "./discoveryPolicyDraft";

const NO_DESCRIPTION = "—";

function sameContent(a: DiscoveryRuleDraft, b: DiscoveryRuleDraft): boolean {
  return JSON.stringify([a.outcome, a.namespaces, a.tableNames]) === JSON.stringify([b.outcome, b.namespaces, b.tableNames]);
}

// Where each rule kept by both versions stands among the kept rules only, so a rule added or
// removed above it does not count as moving it; only a change of order between kept rules does.
function keptRanks(rules: DiscoveryRuleDraft[], kept: Set<string | null>): Map<string | null, number> {
  return new Map(rules.filter((rule) => kept.has(rule.id)).map((rule, rank) => [rule.id, rank]));
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

  const earlier = new Map(before.rules.map((rule, index) => [rule.id, { rule, position: index + 1 }]));
  const laterIds = new Set(after.rules.map((rule) => rule.id));
  const kept = new Set(after.rules.filter((rule) => earlier.has(rule.id)).map((rule) => rule.id));
  const rankBefore = keptRanks(before.rules, kept);
  const rankAfter = keptRanks(after.rules, kept);

  after.rules.forEach((rule, index) => {
    const id = rule.id ?? rule.key;
    const label = `Rule #${index + 1}`;
    const old = earlier.get(rule.id);
    if (old === undefined) {
      items.push({ id, change: "added", label, after: ruleText(rule) });
      return;
    }
    const move = rankBefore.get(rule.id) === rankAfter.get(rule.id) ? null : `Moved from #${old.position} to #${index + 1}`;
    if (!sameContent(old.rule, rule)) {
      items.push({
        id,
        change: "changed",
        label,
        ...(move === null ? {} : { tags: ["Changed", "Moved"] }),
        before: ruleText(old.rule),
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
