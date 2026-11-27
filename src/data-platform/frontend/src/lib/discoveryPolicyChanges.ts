import type { DiffListItem } from "@retail-lakehouse/design-system";
import type { TableDiscoveryPolicyVersionApiResponse } from "@/api/generated/model";
import { draftFromPolicy, ruleText, type DiscoveryRuleDraft } from "./discoveryPolicyDraft";

const NO_DESCRIPTION = "—";

type Step = { kind: "kept"; after: number } | { kind: "added"; after: number } | { kind: "removed"; before: number };

function sameRule(a: DiscoveryRuleDraft, b: DiscoveryRuleDraft): boolean {
  return a.action === b.action && a.tableNamePattern === b.tableNamePattern;
}

// The edit script from `before` to `after` along one longest common subsequence of rules, read as
// (action, pattern) pairs. At one spot a removal comes before an addition, as in a unified diff.
function editScript(before: DiscoveryRuleDraft[], after: DiscoveryRuleDraft[]): Step[] {
  const rows = before.length;
  const columns = after.length;
  // longest[i][j]: the longest common subsequence of before[i..] and after[j..].
  const longest = Array.from({ length: rows + 1 }, () => new Array<number>(columns + 1).fill(0));
  for (let i = rows - 1; i >= 0; i -= 1) {
    for (let j = columns - 1; j >= 0; j -= 1) {
      longest[i]![j] = sameRule(before[i]!, after[j]!)
        ? longest[i + 1]![j + 1]! + 1
        : Math.max(longest[i + 1]![j]!, longest[i]![j + 1]!);
    }
  }
  const steps: Step[] = [];
  let i = 0;
  let j = 0;
  while (i < rows || j < columns) {
    if (i < rows && j < columns && sameRule(before[i]!, after[j]!)) {
      steps.push({ kind: "kept", after: j });
      i += 1;
      j += 1;
    } else if (i < rows && (j === columns || longest[i + 1]![j]! >= longest[i]![j + 1]!)) {
      steps.push({ kind: "removed", before: i });
      i += 1;
    } else {
      steps.push({ kind: "added", after: j });
      j += 1;
    }
  }
  return steps;
}

// What a kept version changed from the one before it: the description when it changed, then every
// rule in order. A rule has no identity across versions, only its action and pattern, so a changed
// or moved rule reads as the old one removed and the new one added. A rule is named by its
// position, "Rule #2": a removed one by where it was, any other by where it is.
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

  for (const step of editScript(before.rules, after.rules)) {
    if (step.kind === "removed") {
      const position = step.before + 1;
      items.push({
        id: `removed-${position}`,
        change: "removed",
        label: `Rule #${position}`,
        before: ruleText(before.rules[step.before]!),
      });
      continue;
    }
    const position = step.after + 1;
    const text = ruleText(after.rules[step.after]!);
    items.push(
      step.kind === "added"
        ? { id: `added-${position}`, change: "added", label: `Rule #${position}`, after: text }
        : { id: `kept-${position}`, change: "unchanged", label: `Rule #${position}`, after: text },
    );
  }

  return items;
}
