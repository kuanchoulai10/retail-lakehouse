import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import {
  getGetApplicableMaintenancePolicyQueryKey,
  getGetTableApplicableMaintenancePolicyQueryKey,
  getGetTableMaintenancePolicyQueryKey,
  getListTableMaintenancePoliciesQueryKey,
  getListTableMaintenancePolicyMappingsQueryKey,
} from "./generated/maintenance-policies/maintenance-policies";
import { getGetTableQueryKey } from "./generated/tables/tables";
import { invalidatePolicyAttachments } from "./invalidatePolicyAttachments";

describe("invalidatePolicyAttachments", () => {
  it("marks what applies anywhere, the policy list and the named policies' mappings stale, nothing else", async () => {
    const client = new QueryClient();
    const keys = {
      catalog: getGetApplicableMaintenancePolicyQueryKey({ catalog: "iceberg" }),
      namespace: getGetApplicableMaintenancePolicyQueryKey({ catalog: "iceberg", namespace: "retail" }),
      table: getGetTableApplicableMaintenancePolicyQueryKey("uuid-orders"),
      list: getListTableMaintenancePoliciesQueryKey(),
      nightly: getListTableMaintenancePolicyMappingsQueryKey("nightly"),
      scratch: getListTableMaintenancePolicyMappingsQueryKey("scratch"),
      other: getListTableMaintenancePolicyMappingsQueryKey("other"),
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
