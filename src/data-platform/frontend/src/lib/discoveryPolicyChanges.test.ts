import { describe, expect, it } from "vitest";
import type { DiscoveryRuleApiResponse, TableDiscoveryPolicyVersionApiResponse } from "@/api/generated/model";
import { discoveryPolicyChanges } from "./discoveryPolicyChanges";

const ORDERS: DiscoveryRuleApiResponse = { action: "include", table_name_pattern: "orders*" };
const TEMPORARY: DiscoveryRuleApiResponse = { action: "exclude", table_name_pattern: "tmp_*" };
const ARCHIVE: DiscoveryRuleApiResponse = { action: "exclude", table_name_pattern: "archive_*" };

function version(
  number: number,
  overrides: Partial<TableDiscoveryPolicyVersionApiResponse> = {},
): TableDiscoveryPolicyVersionApiResponse {
  return {
    id: "dp-01m7s6c3tqee0rhg00xry2zqqv",
    name: "sales-tables",
    version: number,
    description: "Sales tables",
    rules: [ORDERS, TEMPORARY],
    created_at: "2026-11-05T09:00:00Z",
    ...overrides,
  };
}

function changed(items: ReturnType<typeof discoveryPolicyChanges>) {
  return items.filter((item) => item.change !== "unchanged");
}

describe("discoveryPolicyChanges", () => {
  it("lists a rule added and a rule removed, in the order of the rules", () => {
    const items = discoveryPolicyChanges(
      version(1, { rules: [ORDERS, ARCHIVE] }),
      version(2, { rules: [ORDERS, TEMPORARY] }),
    );
    expect(changed(items)).toEqual([
      { id: "removed-2", change: "removed", label: "Rule #2", before: "Exclude archive_*" },
      { id: "added-2", change: "added", label: "Rule #2", after: "Exclude tmp_*" },
    ]);
  });

  it("reads a flipped action as the old rule removed and the new one added", () => {
    const items = discoveryPolicyChanges(
      version(1),
      version(2, { rules: [{ ...ORDERS, action: "exclude" }, TEMPORARY] }),
    );
    expect(changed(items)).toEqual([
      { id: "removed-1", change: "removed", label: "Rule #1", before: "Include orders*" },
      { id: "added-1", change: "added", label: "Rule #1", after: "Exclude orders*" },
    ]);
  });

  it("reads a changed pattern as the old rule removed and the new one added", () => {
    const items = discoveryPolicyChanges(
      version(1),
      version(2, { rules: [ORDERS, { ...TEMPORARY, table_name_pattern: "staging_*" }] }),
    );
    expect(changed(items)).toEqual([
      { id: "removed-2", change: "removed", label: "Rule #2", before: "Exclude tmp_*" },
      { id: "added-2", change: "added", label: "Rule #2", after: "Exclude staging_*" },
    ]);
  });

  it("reads a move as a removal and an addition, keeping the longest run in place", () => {
    const items = discoveryPolicyChanges(
      version(1, { rules: [ORDERS, TEMPORARY, ARCHIVE] }),
      version(2, { rules: [TEMPORARY, ARCHIVE, ORDERS] }),
    );
    expect(changed(items)).toEqual([
      { id: "removed-1", change: "removed", label: "Rule #1", before: "Include orders*" },
      { id: "added-3", change: "added", label: "Rule #3", after: "Include orders*" },
    ]);
  });

  it("does not call the rules after an inserted one changed", () => {
    const items = discoveryPolicyChanges(version(1), version(2, { rules: [ARCHIVE, ORDERS, TEMPORARY] }));
    expect(changed(items)).toEqual([{ id: "added-1", change: "added", label: "Rule #1", after: "Exclude archive_*" }]);
    expect(items.filter((item) => item.change === "unchanged").map((item) => item.label)).toEqual([
      "Rule #2",
      "Rule #3",
    ]);
  });

  it("tells two identical rules apart by position", () => {
    const items = discoveryPolicyChanges(
      version(1, { rules: [ORDERS, ORDERS] }),
      version(2, { rules: [ORDERS] }),
    );
    expect(changed(items)).toEqual([{ id: "removed-2", change: "removed", label: "Rule #2", before: "Include orders*" }]);
  });

  it("shows an empty description as a dash, before or after", () => {
    expect(changed(discoveryPolicyChanges(version(1, { description: "" }), version(2)))).toEqual([
      { id: "description", change: "changed", label: "Description", before: "—", after: "Sales tables" },
    ]);
    expect(changed(discoveryPolicyChanges(version(1), version(2, { description: "" })))).toEqual([
      { id: "description", change: "changed", label: "Description", before: "Sales tables", after: "—" },
    ]);
  });

  it("gives identical versions nothing but unchanged rules", () => {
    const items = discoveryPolicyChanges(version(1), version(2));
    expect(changed(items)).toEqual([]);
    expect(items).toEqual([
      { id: "kept-1", change: "unchanged", label: "Rule #1", after: "Include orders*" },
      { id: "kept-2", change: "unchanged", label: "Rule #2", after: "Exclude tmp_*" },
    ]);
  });
});
