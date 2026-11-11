import type { QueryClient } from "@tanstack/react-query";
import {
  getGetApplicableMaintenancePolicyQueryKey,
  getGetTableApplicableMaintenancePolicyQueryKey,
  getListTableMaintenancePoliciesQueryKey,
  getListTableMaintenancePolicyMappingsQueryKey,
} from "./generated/maintenance-policies/maintenance-policies";

const [CATALOG_APPLICABLE_URL] = getGetApplicableMaintenancePolicyQueryKey();
const TABLE_APPLICABLE_URL = getGetTableApplicableMaintenancePolicyQueryKey("\u0000")[0];
const [TABLE_APPLICABLE_START, TABLE_APPLICABLE_END] = TABLE_APPLICABLE_URL.split("\u0000") as [string, string];

function isTableApplicableKey(key: unknown): boolean {
  return typeof key === "string" && key.startsWith(TABLE_APPLICABLE_START) && key.endsWith(TABLE_APPLICABLE_END);
}

// After an attach or detach: what applies anywhere (one attachment changes it for every target
// below), the policy list (its attachment counts) and where each named policy is attached.
export function invalidatePolicyAttachments(queryClient: QueryClient, policyNames: string[]): Promise<void[]> {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: [CATALOG_APPLICABLE_URL] }),
    queryClient.invalidateQueries({ predicate: (query) => isTableApplicableKey(query.queryKey[0]) }),
    queryClient.invalidateQueries({ queryKey: getListTableMaintenancePoliciesQueryKey(), exact: true }),
    ...policyNames.map((name) =>
      queryClient.invalidateQueries({ queryKey: getListTableMaintenancePolicyMappingsQueryKey(name) }),
    ),
  ]);
}
