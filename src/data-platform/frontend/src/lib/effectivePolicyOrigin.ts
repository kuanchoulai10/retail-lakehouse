import type { PolicyTargetApiResponse } from "@/api/generated/model";
import { targetKind, targetName } from "@/lib/policyPaths";
import { scopePath, type PolicyScope } from "@/lib/policyScope";

// Where the policy of one kind that applies to a page's target comes from: attached to this very
// target, inherited from a namespace or catalog above it, or the platform default. `lead` and
// `from` let a page link the level it is inherited from; `text` is the whole sentence.
export type EffectivePolicyOrigin =
  | { level: "here"; text: string }
  | { level: "default"; text: string }
  | { level: "inherited"; text: string; lead: string; from: PolicyTargetApiResponse };

// A table attachment is keyed by the table's uuid, so it stays the table's across a rename.
function attachedHere(scope: PolicyScope, target: PolicyTargetApiResponse): boolean {
  if (target.type !== scope.type) return false;
  if (scope.type === "table") return target.table_uuid === scope.tableUuid;
  const path = scopePath(scope);
  return target.path.length === path.length && target.path.every((part, index) => part === path[index]);
}

export function effectivePolicyOrigin(
  scope: PolicyScope,
  entry: { target: PolicyTargetApiResponse | null },
): EffectivePolicyOrigin {
  const { target } = entry;
  if (target === null) return { level: "default", text: "Platform default" };
  if (attachedHere(scope, target)) return { level: "here", text: "Attached here" };
  const lead = `From ${targetKind(target)}`;
  return { level: "inherited", text: `${lead} ${targetName(target)}`, lead, from: target };
}
