import type { QueryClient } from "@tanstack/react-query";
import {
  getListTableMaintenancePoliciesQueryKey,
  getListTableMaintenancePolicyAttachmentsQueryKey,
} from "./generated/maintenance-policies/maintenance-policies";
import { invalidateEffectivePolicies } from "./invalidateEffectivePolicies";
import { invalidateTableRecords } from "./invalidateTableRecords";

// After an attach or detach: what applies anywhere (one attachment changes it for every target
// below), the policy list (its attachment counts), where each named policy is attached and the table
// records (an attach can register a table discovery has not seen).
export function invalidatePolicyAttachments(queryClient: QueryClient, policyNames: string[]): Promise<void[]> {
  return Promise.all([
    invalidateEffectivePolicies(queryClient),
    queryClient.invalidateQueries({ queryKey: getListTableMaintenancePoliciesQueryKey(), exact: true }),
    ...policyNames.map((name) =>
      queryClient.invalidateQueries({ queryKey: getListTableMaintenancePolicyAttachmentsQueryKey(name) }),
    ),
    invalidateTableRecords(queryClient),
  ]);
}
