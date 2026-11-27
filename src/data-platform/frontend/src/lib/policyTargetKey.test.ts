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
