import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import { getListTableMaintenancePoliciesQueryKey } from "./generated/maintenance-policies/maintenance-policies";
import {
  getGetEffectivePoliciesQueryKey,
  getGetTableEffectivePoliciesQueryKey,
  getGetTableQueryKey,
  getListTableCommitsQueryKey,
} from "./generated/tables/tables";
import { invalidateEffectivePolicies } from "./invalidateEffectivePolicies";

describe("invalidateEffectivePolicies", () => {
  it("marks every effective-policies answer stale, by location and by table uuid, nothing else", async () => {
    const client = new QueryClient();
    const keys = {
      catalog: getGetEffectivePoliciesQueryKey({ catalog: "iceberg" }),
      namespace: getGetEffectivePoliciesQueryKey({ catalog: "iceberg", namespace: "retail" }),
      table: getGetEffectivePoliciesQueryKey({ catalog: "iceberg", namespace: "retail", table: "orders" }),
      orders: getGetTableEffectivePoliciesQueryKey("uuid-orders"),
      ledger: getGetTableEffectivePoliciesQueryKey("uuid-ledger"),
      record: getGetTableQueryKey("uuid-orders"),
      commits: getListTableCommitsQueryKey("uuid-orders"),
      policies: getListTableMaintenancePoliciesQueryKey(),
    };
    for (const key of Object.values(keys)) client.setQueryData(key, {});

    await invalidateEffectivePolicies(client);

    const stale = Object.entries(keys)
      .filter(([, key]) => client.getQueryState(key)?.isInvalidated)
      .map(([name]) => name);
    expect(stale).toEqual(["catalog", "namespace", "table", "orders", "ledger"]);
  });
});
