import { describe, expect, it } from "vitest";
import { policyTargetKey } from "./policyTargetKey";

describe("policyTargetKey", () => {
  it("tells places apart by type and by each path part, a dot inside a part included", () => {
    const keys = [
      policyTargetKey({ type: "namespace", path: ["iceberg", "sales"] }),
      policyTargetKey({ type: "table", path: ["iceberg", "sales"] }),
      policyTargetKey({ type: "namespace", path: ["iceberg", "sales", "eu"] }),
      policyTargetKey({ type: "namespace", path: ["iceberg", "sales.eu"] }),
    ];
    expect(new Set(keys).size).toBe(keys.length);
  });

  it("gives the same place the same key", () => {
    expect(policyTargetKey({ type: "catalog", path: ["iceberg"] })).toBe(policyTargetKey({ type: "catalog", path: ["iceberg"] }));
  });
});

describe("policyTargetKey for two tables of one name", () => {
  it("tells an old record from a recreated table of the same path by its uuid", () => {
    const path = ["iceberg", "sales", "orders"];
    expect(policyTargetKey({ type: "table", path, table_uuid: "uuid-old" })).not.toBe(
      policyTargetKey({ type: "table", path, table_uuid: "uuid-recreated" }),
    );
  });

  it("gives a place with no uuid, or a null one, the same key", () => {
    expect(policyTargetKey({ type: "namespace", path: ["iceberg", "sales"], table_uuid: null })).toBe(
      policyTargetKey({ type: "namespace", path: ["iceberg", "sales"] }),
    );
  });
});
