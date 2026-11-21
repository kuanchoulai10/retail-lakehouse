import { describe, expect, it } from "vitest";
import type { DiscoveryRuleApiResponse, TableDiscoveryPolicyVersionApiResponse } from "@/api/generated/model";
import { discoveryPolicyChanges } from "./discoveryPolicyChanges";

const ORDERS: DiscoveryRuleApiResponse = {
  id: "dr-orders",
  outcome: "manage",
  conditions: [{ attribute: "namespace", operator: "glob", values: ["sales"] }],
};
const TEMPORARY: DiscoveryRuleApiResponse = {
  id: "dr-temporary",
  outcome: "unmanage",
  conditions: [{ attribute: "table_name", operator: "glob", values: ["tmp_*"] }],
};
const ARCHIVE: DiscoveryRuleApiResponse = {
  id: "dr-archive",
  outcome: "unmanage",
  conditions: [{ attribute: "table_name", operator: "glob", values: ["archive_*"] }],
};

function version(
  number: number,
  overrides: Partial<TableDiscoveryPolicyVersionApiResponse> = {},
): TableDiscoveryPolicyVersionApiResponse {
  return {
    id: "dp-01m7s6c3tqee0rhg00xry2zqqv",
    name: "sales-tables",
    is_default: false,
    version: number,
    description: "Sales tables",
    no_match_outcome: "unmanage",
    rules: [ORDERS, TEMPORARY],
    created_at: "2026-11-05T09:00:00Z",
    ...overrides,
  };
}

function changed(items: ReturnType<typeof discoveryPolicyChanges>) {
  return items.filter((item) => item.change !== "unchanged");
}

describe("discoveryPolicyChanges", () => {
  it("lists a rule added and a rule removed, by id", () => {
    const items = discoveryPolicyChanges(
      version(1, { rules: [ORDERS, ARCHIVE] }),
      version(2, { rules: [ORDERS, TEMPORARY] }),
    );
    expect(changed(items)).toEqual([
      { id: "dr-temporary", change: "added", label: "Rule #2", after: "Do not manage: table name tmp_*" },
      { id: "dr-archive", change: "removed", label: "Rule #2", before: "Do not manage: table name archive_*" },
    ]);
  });

  it("reads a flipped outcome as changed, before and after in one line", () => {
    const items = discoveryPolicyChanges(
      version(1),
      version(2, { rules: [{ ...ORDERS, outcome: "unmanage" }, TEMPORARY] }),
    );
    expect(changed(items)).toEqual([
      {
        id: "dr-orders",
        change: "changed",
        label: "Rule #1",
        before: "Manage: namespace sales",
        after: "Do not manage: namespace sales",
      },
    ]);
  });

  it("reads a changed condition as changed", () => {
    const wider = { ...TEMPORARY, conditions: [{ ...TEMPORARY.conditions[0]!, values: ["tmp_*", "staging_*"] }] };
    const items = discoveryPolicyChanges(version(1), version(2, { rules: [ORDERS, wider] }));
    expect(changed(items)).toEqual([
      {
        id: "dr-temporary",
        change: "changed",
        label: "Rule #2",
        before: "Do not manage: table name tmp_*",
        after: "Do not manage: table name tmp_*, staging_*",
      },
    ]);
  });

  it("reads a changed namespace glob as changed", () => {
    const sales = { ...ORDERS, conditions: [{ ...ORDERS.conditions[0]!, values: ["sales", "sales.*"] }] };
    const items = discoveryPolicyChanges(version(1), version(2, { rules: [sales, TEMPORARY] }));
    expect(changed(items)).toEqual([
      {
        id: "dr-orders",
        change: "changed",
        label: "Rule #1",
        before: "Manage: namespace sales",
        after: "Manage: namespace sales, sales.*",
      },
    ]);
  });

  it("reads a swap as one rule moved above the other", () => {
    const items = discoveryPolicyChanges(version(1), version(2, { rules: [TEMPORARY, ORDERS] }));
    expect(changed(items)).toEqual([
      {
        id: "dr-temporary",
        change: "changed",
        label: "Rule #1",
        tags: ["Moved"],
        after: "Moved above Manage: namespace sales",
      },
    ]);
  });

  it("reads [A, B, C] to [N, B, A, C] as one added rule and one move, by its new neighbour", () => {
    const added: DiscoveryRuleApiResponse = {
      id: "dr-new",
      outcome: "manage",
      conditions: [{ attribute: "table_name", operator: "glob", values: ["new_*"] }],
    };
    const items = discoveryPolicyChanges(
      version(1, { rules: [ORDERS, TEMPORARY, ARCHIVE] }),
      version(2, { rules: [added, TEMPORARY, ORDERS, ARCHIVE] }),
    );
    expect(changed(items)).toEqual([
      { id: "dr-new", change: "added", label: "Rule #1", after: "Manage: table name new_*" },
      {
        id: "dr-temporary",
        change: "changed",
        label: "Rule #2",
        tags: ["Moved"],
        after: "Moved above Manage: namespace sales",
      },
    ]);
  });

  it("reads the first rule moved to the bottom as one move to the end", () => {
    const items = discoveryPolicyChanges(
      version(1, { rules: [ORDERS, TEMPORARY, ARCHIVE] }),
      version(2, { rules: [TEMPORARY, ARCHIVE, ORDERS] }),
    );
    expect(changed(items)).toEqual([
      { id: "dr-orders", change: "changed", label: "Rule #3", tags: ["Moved"], after: "Moved to the end" },
    ]);
  });

  it("does not call the rules after an inserted one moved", () => {
    const items = discoveryPolicyChanges(version(1), version(2, { rules: [ARCHIVE, ORDERS, TEMPORARY] }));
    expect(changed(items).map((item) => [item.id, item.change])).toEqual([["dr-archive", "added"]]);
  });

  it("says a rule both changed and moved in one item", () => {
    const flipped = { ...ORDERS, outcome: "unmanage" as const };
    const items = discoveryPolicyChanges(
      version(1, { rules: [ORDERS, TEMPORARY, ARCHIVE] }),
      version(2, { rules: [TEMPORARY, ARCHIVE, flipped] }),
    );
    expect(changed(items)).toEqual([
      {
        id: "dr-orders",
        change: "changed",
        label: "Rule #3",
        tags: ["Changed", "Moved"],
        before: "Manage: namespace sales",
        after: "Do not manage: namespace sales",
        description: "Moved to the end",
      },
    ]);
  });

  it("shows an empty description as a dash, before or after", () => {
    const items = discoveryPolicyChanges(version(1, { description: "" }), version(2));
    expect(changed(items)).toEqual([
      { id: "description", change: "changed", label: "Description", before: "—", after: "Sales tables" },
    ]);
  });

  it("lists the no-match outcome and the description when they changed", () => {
    const items = discoveryPolicyChanges(
      version(1),
      version(2, { no_match_outcome: "manage", description: "" }),
    );
    expect(changed(items)).toEqual([
      { id: "description", change: "changed", label: "Description", before: "Sales tables", after: "—" },
      { id: "no-match-outcome", change: "changed", label: "When no rule matches", before: "Do not manage", after: "Manage" },
    ]);
  });

  it("gives identical versions nothing but unchanged rules", () => {
    const items = discoveryPolicyChanges(version(1), version(2));
    expect(changed(items)).toEqual([]);
    expect(items).toEqual([
      { id: "dr-orders", change: "unchanged", label: "Rule #1", after: "Manage: namespace sales" },
      { id: "dr-temporary", change: "unchanged", label: "Rule #2", after: "Do not manage: table name tmp_*" },
    ]);
  });
});
