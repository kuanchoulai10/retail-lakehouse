import type { QueryClient } from "@tanstack/react-query";
import {
  getListTableMaintenancePoliciesQueryKey,
  getListTableMaintenancePolicyAttachmentsQueryKey,
} from "./generated/maintenance-policies/maintenance-policies";
import { invalidateEffectivePolicies } from "./invalidateEffectivePolicies";

// After an attach or detach: what applies anywhere (one attachment changes it for every target
// below), the policy list (its attachment counts) and where each named policy is attached.
export function invalidatePolicyAttachments(queryClient: QueryClient, policyNames: string[]): Promise<void[]> {
  return Promise.all([
    invalidateEffectivePolicies(queryClient),
    queryClient.invalidateQueries({ queryKey: getListTableMaintenancePoliciesQueryKey(), exact: true }),
    ...policyNames.map((name) =>
      queryClient.invalidateQueries({ queryKey: getListTableMaintenancePolicyAttachmentsQueryKey(name) }),
    ),
  ]);
}
