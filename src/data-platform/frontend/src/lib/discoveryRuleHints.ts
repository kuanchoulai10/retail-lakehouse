import { ruleHasCondition, type DiscoveryRuleDraft } from "./discoveryPolicyDraft";
import { targetName, type PolicyTargetRef } from "./policyPaths";

const TABLE_HINT = "On a table, a rule either always or never matches it.";

function namespaceHint(namespace: PolicyTargetRef): string {
  return `Attached to namespace ${targetName(namespace)}: a namespace glob only tells its child namespaces apart.`;
}

// The conditions of a rule that cannot tell tables apart where the policy is attached (ADR 0012:
// the API accepts every condition, the console hints). Attached to a table, a rule decides one
// table, so it always or never matches; attached to a namespace, every table below shares its
// name, so a namespace glob only tells the child namespaces apart. Each hint is given once.
export function ruleHints(rule: DiscoveryRuleDraft, attachments: PolicyTargetRef[]): string[] {
  const hints: string[] = [];
  if (ruleHasCondition(rule) && attachments.some((target) => target.type === "table")) hints.push(TABLE_HINT);
  const namespace = attachments.find((target) => target.type === "namespace");
  if (namespace !== undefined && rule.namespaces.length > 0) hints.push(namespaceHint(namespace));
  return hints;
}
