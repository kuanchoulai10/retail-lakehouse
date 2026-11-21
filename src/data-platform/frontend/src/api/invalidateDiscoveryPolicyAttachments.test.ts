import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import { getListCatalogsQueryKey } from "./generated/catalogs/catalogs";
import {
  getGetTableDiscoveryPolicyQueryKey,
  getGetTableDiscoveryPolicyVersionQueryKey,
  getListScannedCatalogsQueryKey,
  getListTableDiscoveryPoliciesQueryKey,
  getListTableDiscoveryPolicyAttachmentsQueryKey,
} from "./generated/discovery-policies/discovery-policies";
import { invalidateDiscoveryPolicyAttachments } from "./invalidateDiscoveryPolicyAttachments";

describe("invalidateDiscoveryPolicyAttachments", () => {
  it("marks every policy's attachments, the policy list and the scanned catalogs stale, nothing else", async () => {
    const client = new QueryClient();
    const keys = {
      sales: getListTableDiscoveryPolicyAttachmentsQueryKey("sales-tables"),
      finance: getListTableDiscoveryPolicyAttachmentsQueryKey("finance"),
      list: getListTableDiscoveryPoliciesQueryKey(),
      scanned: getListScannedCatalogsQueryKey(),
      policy: getGetTableDiscoveryPolicyQueryKey("sales-tables"),
      version: getGetTableDiscoveryPolicyVersionQueryKey("x", 1),
      catalogs: getListCatalogsQueryKey(),
    };
    for (const key of Object.values(keys)) client.setQueryData(key, {});

    await invalidateDiscoveryPolicyAttachments(client);

    const stale = Object.entries(keys)
      .filter(([, key]) => client.getQueryState(key)?.isInvalidated)
      .map(([name]) => name);
    expect(stale).toEqual(["sales", "finance", "list", "scanned"]);
  });
});
