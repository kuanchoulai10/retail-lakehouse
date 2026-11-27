import type {
  DiscoveryRuleApiResponse,
  TableDiscoveryPolicyApiResponse,
  UpdateTableDiscoveryPolicyApiRequest,
} from "@/api/generated/model";

export type RuleAction = "include" | "exclude";

// One rule as the page edits it. A rule has no id of its own: `key` only names its row on the page,
// and the rule is its action and its table name pattern, at its position.
export interface DiscoveryRuleDraft {
  key: string;
  action: RuleAction;
  tableNamePattern: string;
}

// The policy's content as the page edits it, with the version it was read at.
export interface DiscoveryPolicyDraft {
  version: number;
  description: string;
  rules: DiscoveryRuleDraft[];
}

// The content a policy and each of its kept versions share.
type PolicyContent = Pick<TableDiscoveryPolicyApiResponse, "version" | "description" | "rules">;

const ACTION_LABELS: Record<RuleAction, string> = {
  include: "Include",
  exclude: "Exclude",
};

// The one place a rule's action gets its words.
export function actionLabel(action: RuleAction): string {
  return ACTION_LABELS[action];
}

function actionOf(value: string): RuleAction {
  return value === "include" ? "include" : "exclude";
}

function draftFromRule(rule: DiscoveryRuleApiResponse, index: number): DiscoveryRuleDraft {
  return { key: `rule-${index + 1}`, action: actionOf(rule.action), tableNamePattern: rule.table_name_pattern };
}

export function draftFromPolicy(policy: PolicyContent): DiscoveryPolicyDraft {
  return {
    version: policy.version,
    description: policy.description,
    rules: policy.rules.map(draftFromRule),
  };
}

// The draft as the API takes it: the rules in the draft's order.
export function updateRequest(draft: DiscoveryPolicyDraft): UpdateTableDiscoveryPolicyApiRequest {
  return {
    version: draft.version,
    description: draft.description,
    rules: draft.rules.map((rule) => ({ action: rule.action, table_name_pattern: rule.tableNamePattern })),
  };
}

// A new rule includes and has no pattern yet: the user names what it matches.
export function newRuleDraft(key: string): DiscoveryRuleDraft {
  return { key, action: "include", tableNamePattern: "" };
}

// The rules with the one keyed `key` swapped with its neighbour; at an end, the rules unchanged.
export function movedRule(rules: DiscoveryRuleDraft[], key: string, by: -1 | 1): DiscoveryRuleDraft[] {
  const index = rules.findIndex((rule) => rule.key === key);
  const target = index + by;
  if (index === -1 || target < 0 || target >= rules.length) return rules;
  const next = [...rules];
  [next[index], next[target]] = [next[target]!, next[index]!];
  return next;
}

// The API keeps a policy only with at least one rule; the page also waits for every pattern.
export function isDraftComplete(draft: Pick<DiscoveryPolicyDraft, "rules">): boolean {
  return draft.rules.length > 0 && draft.rules.every((rule) => rule.tableNamePattern.trim() !== "");
}

// A rule in one line, as the version page compares rules: "Exclude tmp_*".
export function ruleText(rule: Pick<DiscoveryRuleDraft, "action" | "tableNamePattern">): string {
  return `${actionLabel(rule.action)} ${rule.tableNamePattern}`;
}
