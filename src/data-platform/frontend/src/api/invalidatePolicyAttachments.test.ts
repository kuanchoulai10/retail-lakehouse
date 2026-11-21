import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import {
  getGetTableMaintenancePolicyQueryKey,
  getListTableMaintenancePoliciesQueryKey,
  getListTableMaintenancePolicyAttachmentsQueryKey,
} from "./generated/maintenance-policies/maintenance-policies";
import {
  getGetEffectivePoliciesQueryKey,
  getGetTableEffectivePoliciesQueryKey,
  getGetTableQueryKey,
} from "./generated/tables/tables";
import { invalidatePolicyAttachments } from "./invalidatePolicyAttachments";

describe("invalidatePolicyAttachments", () => {
  it("marks what applies anywhere, the policy list and the named policies' attachments stale, nothing else", async () => {
    const client = new QueryClient();
    const keys = {
      catalog: getGetEffectivePoliciesQueryKey({ catalog: "iceberg" }),
      namespace: getGetEffectivePoliciesQueryKey({ catalog: "iceberg", namespace: "retail" }),
      table: getGetTableEffectivePoliciesQueryKey("uuid-orders"),
      list: getListTableMaintenancePoliciesQueryKey(),
      nightly: getListTableMaintenancePolicyAttachmentsQueryKey("nightly"),
      scratch: getListTableMaintenancePolicyAttachmentsQueryKey("scratch"),
      other: getListTableMaintenancePolicyAttachmentsQueryKey("other"),
      policy: getGetTableMaintenancePolicyQueryKey("nightly"),
      record: getGetTableQueryKey("uuid-orders"),
    };
    for (const key of Object.values(keys)) client.setQueryData(key, {});

    await invalidatePolicyAttachments(client, ["nightly", "scratch"]);

    const stale = Object.entries(keys)
      .filter(([, key]) => client.getQueryState(key)?.isInvalidated)
      .map(([name]) => name);
    expect(stale).toEqual(["catalog", "namespace", "table", "list", "nightly", "scratch"]);
  });
});
