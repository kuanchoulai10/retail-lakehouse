import type { DetachTableDiscoveryPolicyParams, DetachTableMaintenancePolicyParams } from "@/api/generated/model";
import type { PolicyTargetRef } from "@/lib/policyPaths";

// The catalog, namespace or table to detach a policy from, as either kind's detach query names it:
// its type, and its path repeated once per part (the catalog, the namespace levels, then the table).
export function detachPlace(target: PolicyTargetRef): DetachTableDiscoveryPolicyParams & DetachTableMaintenancePolicyParams {
  return { target_type: target.type, path: target.path };
}
