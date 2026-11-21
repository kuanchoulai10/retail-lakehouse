import type {
  DiscoveryConditionApiRequest,
  DiscoveryRuleApiRequest,
  DiscoveryRuleApiResponse,
  TableDiscoveryPolicyApiResponse,
  UpdateTableDiscoveryPolicyApiRequest,
} from "@/api/generated/model";

export type DiscoveryOutcome = "manage" | "unmanage";

// One rule as the page edits it. `key` names it on the page; `id` is the server's `dr-` id, null
// until the rule is saved (the server issues ids, so a new rule is sent without one). An empty glob
// list means the rule puts no condition on that attribute.
export interface DiscoveryRuleDraft {
  key: string;
  id: string | null;
  outcome: DiscoveryOutcome;
  namespaces: string[];
  tableNames: string[];
}

// The policy's content as the page edits it, with the version it was read at.
export interface DiscoveryPolicyDraft {
  version: number;
  description: string;
  noMatchOutcome: DiscoveryOutcome;
  rules: DiscoveryRuleDraft[];
}

// The content a policy and each of its kept versions share.
type PolicyContent = Pick<TableDiscoveryPolicyApiResponse, "version" | "description" | "no_match_outcome" | "rules">;

const OUTCOME_LABELS: Record<DiscoveryOutcome, string> = {
  manage: "Manage",
  unmanage: "Do not manage",
};

export function outcomeLabel(outcome: DiscoveryOutcome): string {
  return OUTCOME_LABELS[outcome];
}

function outcomeOf(value: string): DiscoveryOutcome {
  return value === "manage" ? "manage" : "unmanage";
}

function globsOf(rule: DiscoveryRuleApiResponse, attribute: DiscoveryConditionApiRequest["attribute"]): string[] {
  return rule.conditions.find((condition) => condition.attribute === attribute)?.values ?? [];
}

export function draftFromRule(rule: DiscoveryRuleApiResponse): DiscoveryRuleDraft {
  return {
    key: rule.id,
    id: rule.id,
    outcome: outcomeOf(rule.outcome),
    namespaces: globsOf(rule, "namespace"),
    tableNames: globsOf(rule, "table_name"),
  };
}

export function draftFromPolicy(policy: PolicyContent): DiscoveryPolicyDraft {
  return {
    version: policy.version,
    description: policy.description,
    noMatchOutcome: outcomeOf(policy.no_match_outcome),
    rules: policy.rules.map(draftFromRule),
  };
}

// Only the conditions the rule has, namespace first, each a glob match.
function conditionsOf(rule: DiscoveryRuleDraft): DiscoveryConditionApiRequest[] {
  const conditions: DiscoveryConditionApiRequest[] = [];
  if (rule.namespaces.length > 0) conditions.push({ attribute: "namespace", operator: "glob", values: rule.namespaces });
  if (rule.tableNames.length > 0) conditions.push({ attribute: "table_name", operator: "glob", values: rule.tableNames });
  return conditions;
}

function ruleRequest(rule: DiscoveryRuleDraft): DiscoveryRuleApiRequest {
  return { ...(rule.id === null ? {} : { id: rule.id }), outcome: rule.outcome, conditions: conditionsOf(rule) };
}

// The draft as the API takes it: the rules in the draft's order, a new rule without an id.
export function updateRequest(draft: DiscoveryPolicyDraft): UpdateTableDiscoveryPolicyApiRequest {
  return {
    version: draft.version,
    description: draft.description,
    no_match_outcome: draft.noMatchOutcome,
    rules: draft.rules.map(ruleRequest),
  };
}

// A new rule with no globs: the user names what it matches.
export function newRuleDraft(key: string): DiscoveryRuleDraft {
  return { key, id: null, outcome: "manage", namespaces: [], tableNames: [] };
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

// The API refuses a rule without a condition; the editor says so first.
export function ruleHasCondition(rule: DiscoveryRuleDraft): boolean {
  return rule.namespaces.length > 0 || rule.tableNames.length > 0;
}

// A rule in one line, as the version page compares rules: "Manage: namespace sales; table name orders*".
export function ruleText(rule: DiscoveryRuleDraft): string {
  const conditions = [
    ...(rule.namespaces.length > 0 ? [`namespace ${rule.namespaces.join(", ")}`] : []),
    ...(rule.tableNames.length > 0 ? [`table name ${rule.tableNames.join(", ")}`] : []),
  ];
  return `${outcomeLabel(rule.outcome)}: ${conditions.length > 0 ? conditions.join("; ") : "every table"}`;
}
