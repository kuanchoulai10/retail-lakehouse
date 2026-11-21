import { describe, expect, it } from "vitest";
import { newRuleDraft, type DiscoveryRuleDraft } from "./discoveryPolicyDraft";
import { ruleHints } from "./discoveryRuleHints";

const TABLE_HINT = "On a table, a rule either always or never matches it.";

function rule(overrides: Partial<DiscoveryRuleDraft> = {}): DiscoveryRuleDraft {
  return { ...newRuleDraft("r1"), ...overrides };
}

describe("ruleHints", () => {
  it("gives no hint where every condition can tell tables apart", () => {
    const attachments = [
      { type: "catalog", path: ["iceberg"] },
      { type: "catalog", path: ["analytics"] },
    ];
    expect(ruleHints(rule({ namespaces: ["sales"], tableNames: ["orders*"] }), attachments)).toEqual([]);
  });

  it("gives no hint while the policy is attached nowhere", () => {
    expect(ruleHints(rule({ namespaces: ["sales"], tableNames: ["orders*"] }), [])).toEqual([]);
  });

  it("says a rule always or never matches a table it is attached to, once however many tables", () => {
    const attachments = [
      { type: "table", path: ["iceberg", "sales", "orders"] },
      { type: "table", path: ["iceberg", "sales", "returns"] },
    ];
    expect(ruleHints(rule({ tableNames: ["orders*"] }), attachments)).toEqual([TABLE_HINT]);
  });

  it("gives the table hint only to a rule with a condition", () => {
    expect(ruleHints(rule(), [{ type: "table", path: ["iceberg", "sales", "orders"] }])).toEqual([]);
  });

  it("names the first namespace attached for a rule with a namespace glob, once", () => {
    const attachments = [
      { type: "catalog", path: ["iceberg"] },
      { type: "namespace", path: ["iceberg", "sales"] },
      { type: "namespace", path: ["iceberg", "finance", "eu"] },
    ];
    expect(ruleHints(rule({ namespaces: ["sales", "sales.*"] }), attachments)).toEqual([
      "Attached to namespace iceberg.sales: a namespace glob only tells its child namespaces apart.",
    ]);
  });

  it("gives no namespace hint to a rule without a namespace glob", () => {
    expect(ruleHints(rule({ tableNames: ["orders*"] }), [{ type: "namespace", path: ["iceberg", "sales"] }])).toEqual(
      [],
    );
  });

  it("gives both hints when the policy is on a table and a namespace", () => {
    const attachments = [
      { type: "namespace", path: ["iceberg", "sales"] },
      { type: "table", path: ["iceberg", "finance", "ledger"] },
    ];
    expect(ruleHints(rule({ namespaces: ["sales"] }), attachments)).toEqual([
      TABLE_HINT,
      "Attached to namespace iceberg.sales: a namespace glob only tells its child namespaces apart.",
    ]);
  });
});
