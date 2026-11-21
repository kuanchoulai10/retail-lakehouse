import { describe, expect, it } from "vitest";
import type { PolicyTargetApiResponse } from "@/api/generated/model";
import { effectivePolicyOrigin } from "./effectivePolicyOrigin";
import type { PolicyScope } from "./policyScope";

const CATALOG: PolicyScope = { type: "catalog", catalog: "iceberg" };
const NAMESPACE: PolicyScope = { type: "namespace", catalog: "iceberg", namespace: ["retail", "eu"] };
const TABLE: PolicyScope = {
  type: "table",
  catalog: "iceberg",
  namespace: ["retail"],
  table: "orders",
  tableUuid: "uuid-orders",
  recorded: true,
};

const AT_CATALOG: PolicyTargetApiResponse = { type: "catalog", path: ["iceberg"], table_uuid: null };
const AT_RETAIL: PolicyTargetApiResponse = { type: "namespace", path: ["iceberg", "retail"], table_uuid: null };
const AT_RETAIL_EU: PolicyTargetApiResponse = { type: "namespace", path: ["iceberg", "retail", "eu"], table_uuid: null };

function originText(scope: PolicyScope, target: PolicyTargetApiResponse | null): string {
  return effectivePolicyOrigin(scope, { target }).text;
}

describe("effectivePolicyOrigin", () => {
  it("names the platform default when nothing is attached here or above", () => {
    expect(effectivePolicyOrigin(TABLE, { target: null })).toEqual({ level: "default", text: "Platform default" });
  });

  it("says attached here for the page's own catalog, namespace or table", () => {
    expect(originText(CATALOG, AT_CATALOG)).toBe("Attached here");
    expect(originText(NAMESPACE, AT_RETAIL_EU)).toBe("Attached here");
    expect(
      originText(TABLE, { type: "table", path: ["iceberg", "retail", "orders"], table_uuid: "uuid-orders" }),
    ).toBe("Attached here");
  });

  it("names the namespace or catalog a policy comes from", () => {
    expect(effectivePolicyOrigin(TABLE, { target: AT_RETAIL })).toEqual({
      level: "inherited",
      text: "From namespace iceberg.retail",
      lead: "From namespace",
      from: AT_RETAIL,
    });
    expect(originText(TABLE, AT_CATALOG)).toBe("From catalog iceberg");
    expect(originText(NAMESPACE, AT_CATALOG)).toBe("From catalog iceberg");
  });

  it("reads a parent namespace as inherited, not as attached here", () => {
    expect(originText(NAMESPACE, AT_RETAIL)).toBe("From namespace iceberg.retail");
  });

  it("compares a table attachment by uuid, so it stays the table's across a rename", () => {
    const renamed: PolicyTargetApiResponse = { type: "table", path: ["iceberg", "retail", "orders_old"], table_uuid: "uuid-orders" };
    expect(originText(TABLE, renamed)).toBe("Attached here");
    const sameNameOtherTable: PolicyTargetApiResponse = {
      type: "table",
      path: ["iceberg", "retail", "orders"],
      table_uuid: "uuid-other",
    };
    expect(effectivePolicyOrigin(TABLE, { target: sameNameOtherTable }).level).toBe("inherited");
  });
});
