import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import {
  getGetEffectivePoliciesQueryKey,
  getGetTableCurrentMetricsQueryKey,
  getGetTableEffectivePoliciesQueryKey,
  getGetTableQueryKey,
  getListTableCommitsQueryKey,
  getListTablesQueryKey,
} from "./generated/tables/tables";
import { invalidateTableRecords } from "./invalidateTableRecords";

describe("invalidateTableRecords", () => {
  it("marks every table record and every table listing stale, and nothing read below a record", async () => {
    const client = new QueryClient();
    const keys = {
      orders: getGetTableQueryKey("uuid-orders"),
      ledger: getGetTableQueryKey("uuid-ledger"),
      tables: getListTablesQueryKey(),
      managed: getListTablesQueryKey({ status: "managed" }),
      commits: getListTableCommitsQueryKey("uuid-orders"),
      metrics: getGetTableCurrentMetricsQueryKey("uuid-orders"),
      tableEffective: getGetTableEffectivePoliciesQueryKey("uuid-orders"),
      effective: getGetEffectivePoliciesQueryKey({ catalog: "iceberg" }),
    };
    for (const key of Object.values(keys)) client.setQueryData(key, {});

    await invalidateTableRecords(client);

    const stale = Object.entries(keys)
      .filter(([, key]) => client.getQueryState(key)?.isInvalidated)
      .map(([name]) => name);
    expect(stale).toEqual(["orders", "ledger", "tables", "managed"]);
  });
});
