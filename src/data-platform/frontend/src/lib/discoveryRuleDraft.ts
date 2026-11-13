import type { TableDiscoveryRuleApiRequest, TableDiscoveryRuleApiResponse } from "@/api/generated/model";

export type DiscoveryRuleAction = "include" | "exclude";

// One rule as the page edits it. `key` names it on the page; `id` is the server's id, null
// until the rule is saved (the server generates ids, so a new rule is sent without one).
export interface DiscoveryRuleDraft {
  key: string;
  id: string | null;
  priority: number;
  action: DiscoveryRuleAction;
  enabled: boolean;
  catalogs: string[];
  namespaces: string[];
  tables: string[];
}

export function draftFromRule(rule: TableDiscoveryRuleApiResponse): DiscoveryRuleDraft {
  return {
    key: rule.id,
    id: rule.id,
    priority: rule.priority,
    action: rule.action === "exclude" ? "exclude" : "include",
    enabled: rule.enabled,
    catalogs: rule.catalogs,
    namespaces: rule.namespaces,
    tables: rule.tables,
  };
}

// Lowest priority first, the order the server applies rules in; stable for equal priorities.
export function inPriorityOrder(rules: DiscoveryRuleDraft[]): DiscoveryRuleDraft[] {
  return [...rules].sort((a, b) => a.priority - b.priority);
}

// The list as the API takes it: in priority order, a new rule without an id.
export function rulesRequest(rules: DiscoveryRuleDraft[]): TableDiscoveryRuleApiRequest[] {
  return inPriorityOrder(rules).map((rule) => ({
    ...(rule.id === null ? {} : { id: rule.id }),
    priority: rule.priority,
    action: rule.action,
    enabled: rule.enabled,
    catalogs: rule.catalogs,
    namespaces: rule.namespaces,
    tables: rule.tables,
  }));
}

// A new rule after the others, with no globs: the user names what it matches.
export function newRuleDraft(rules: DiscoveryRuleDraft[], key: string): DiscoveryRuleDraft {
  const last = Math.max(0, ...rules.map((rule) => rule.priority));
  return {
    key,
    id: null,
    priority: last + 10,
    action: "include",
    enabled: true,
    catalogs: [],
    namespaces: [],
    tables: [],
  };
}
