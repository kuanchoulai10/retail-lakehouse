import { describe, expect, it } from "vitest";
import type { TableDiscoveryPolicyApiResponse } from "@/api/generated/model";
import {
  draftFromPolicy,
  movedRule,
  newRuleDraft,
  ruleHasCondition,
  ruleText,
  updateRequest,
} from "./discoveryPolicyDraft";

const TEMPORARY_RULE_ID = "dr-01m7s6c3tqee0rhg00xz1dk9cs";

const POLICY: TableDiscoveryPolicyApiResponse = {
  id: "dp-01m7s6c3tqee0rhg00xry2zqqv",
  name: "sales-tables",
  is_default: false,
  version: 2,
  description: "Sales tables, without the temporary ones",
  no_match_outcome: "unmanage",
  rules: [
    {
      id: "dr-01m7s6c3tqee0rhg00xry2zqqt",
      outcome: "manage",
      conditions: [
        { attribute: "namespace", operator: "glob", values: ["sales", "sales.*"] },
        { attribute: "table_name", operator: "glob", values: ["orders*"] },
      ],
    },
    {
      id: TEMPORARY_RULE_ID,
      outcome: "unmanage",
      conditions: [{ attribute: "table_name", operator: "glob", values: ["tmp_*", "staging_*"] }],
    },
  ],
  created_at: "2026-11-01T09:00:00Z",
  updated_at: "2026-11-05T09:00:00Z",
};

describe("discoveryPolicyDraft", () => {
  it("turns a policy into a draft and back into the same content", () => {
    const draft = draftFromPolicy(POLICY);
    expect(draft.version).toBe(2);
    expect(draft.rules.map((rule) => rule.key)).toEqual([
      "dr-01m7s6c3tqee0rhg00xry2zqqt",
      "dr-01m7s6c3tqee0rhg00xz1dk9cs",
    ]);
    expect(draft.rules[1]).toEqual({
      key: TEMPORARY_RULE_ID,
      id: TEMPORARY_RULE_ID,
      outcome: "unmanage",
      namespaces: [],
      tableNames: ["tmp_*", "staging_*"],
    });
    expect(updateRequest(draft)).toEqual({
      version: 2,
      description: POLICY.description,
      no_match_outcome: "unmanage",
      rules: POLICY.rules,
    });
  });

  it("sends a new rule without an id", () => {
    const draft = draftFromPolicy(POLICY);
    const added = { ...newRuleDraft("new-1"), namespaces: ["finance"] };
    const request = updateRequest({ ...draft, rules: [...draft.rules, added] });
    expect(request.rules[2]).toEqual({
      outcome: "manage",
      conditions: [{ attribute: "namespace", operator: "glob", values: ["finance"] }],
    });
    expect(request.rules[2]).not.toHaveProperty("id");
  });

  it("sends a rule with only table name globs as one table_name condition", () => {
    const rule = { ...newRuleDraft("new-1"), outcome: "unmanage" as const, tableNames: ["tmp_*"] };
    const request = updateRequest({ version: 1, description: "", noMatchOutcome: "manage", rules: [rule] });
    expect(request.rules).toEqual([
      { outcome: "unmanage", conditions: [{ attribute: "table_name", operator: "glob", values: ["tmp_*"] }] },
    ]);
  });

  it("keeps the draft's rule order and its description and no-match outcome", () => {
    const draft = draftFromPolicy(POLICY);
    const request = updateRequest({
      ...draft,
      description: "Only orders",
      noMatchOutcome: "manage",
      rules: [draft.rules[1]!, draft.rules[0]!],
    });
    expect(request.description).toBe("Only orders");
    expect(request.no_match_outcome).toBe("manage");
    expect(request.rules.map((rule) => rule.id)).toEqual([
      "dr-01m7s6c3tqee0rhg00xz1dk9cs",
      "dr-01m7s6c3tqee0rhg00xry2zqqt",
    ]);
  });

  it("starts a new rule as manage with no globs", () => {
    const rule = newRuleDraft("new-7");
    expect(rule).toEqual({ key: "new-7", id: null, outcome: "manage", namespaces: [], tableNames: [] });
    expect(ruleHasCondition(rule)).toBe(false);
    expect(ruleHasCondition({ ...rule, tableNames: ["*"] })).toBe(true);
    expect(ruleHasCondition({ ...rule, namespaces: ["*"] })).toBe(true);
  });

  it("moves a rule one place up or down and leaves the ends alone", () => {
    const rules = ["a", "b", "c"].map((key) => ({ ...newRuleDraft(key), namespaces: [key] }));
    expect(movedRule(rules, "c", -1).map((rule) => rule.key)).toEqual(["a", "c", "b"]);
    expect(movedRule(rules, "a", 1).map((rule) => rule.key)).toEqual(["b", "a", "c"]);
    expect(movedRule(rules, "a", -1)).toBe(rules);
    expect(movedRule(rules, "c", 1)).toBe(rules);
    expect(movedRule(rules, "missing", 1)).toBe(rules);
  });

  it("reads a rule in one line, outcome first", () => {
    const [orders, temporary] = draftFromPolicy(POLICY).rules;
    expect(ruleText(orders!)).toBe("Manage: namespace sales, sales.*; table name orders*");
    expect(ruleText(temporary!)).toBe("Do not manage: table name tmp_*, staging_*");
  });
});
