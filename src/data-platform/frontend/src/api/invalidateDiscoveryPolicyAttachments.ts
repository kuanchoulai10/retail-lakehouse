import type { QueryClient } from "@tanstack/react-query";
import {
  getListScannedCatalogsQueryKey,
  getListTableDiscoveryPoliciesQueryKey,
  getListTableDiscoveryPolicyAttachmentsQueryKey,
} from "./generated/discovery-policies/discovery-policies";

const ATTACHMENTS_URL = getListTableDiscoveryPolicyAttachmentsQueryKey("\u0000")[0];
const [ATTACHMENTS_START, ATTACHMENTS_END] = ATTACHMENTS_URL.split("\u0000") as [string, string];

function isAttachmentsKey(key: unknown): boolean {
  return typeof key === "string" && key.startsWith(ATTACHMENTS_START) && key.endsWith(ATTACHMENTS_END);
}

// After a discovery attach or detach: every policy's attachments (an attach replaces whichever
// policy the target held), the policy list (its attachment counts) and the scanned catalogs (the
// change can start or stop a catalog's scans).
export function invalidateDiscoveryPolicyAttachments(queryClient: QueryClient): Promise<void[]> {
  return Promise.all([
    queryClient.invalidateQueries({ predicate: (query) => isAttachmentsKey(query.queryKey[0]) }),
    queryClient.invalidateQueries({ queryKey: getListTableDiscoveryPoliciesQueryKey(), exact: true }),
    queryClient.invalidateQueries({ queryKey: getListScannedCatalogsQueryKey() }),
  ]);
}
