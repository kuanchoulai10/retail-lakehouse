import { describe, expect, it } from "vitest";
import type { TableDiscoveryPolicyApiResponse } from "@/api/generated/model";
import {
  actionLabel,
  draftFromPolicy,
  isDraftComplete,
  movedRule,
  newRuleDraft,
  ruleText,
  updateRequest,
} from "./discoveryPolicyDraft";

const POLICY: TableDiscoveryPolicyApiResponse = {
  id: "dp-01m7s6c3tqee0rhg00xry2zqqv",
  name: "sales-tables",
  version: 2,
  description: "Sales tables, without the temporary ones",
  rules: [
    { action: "include", table_name_pattern: "orders*" },
    { action: "exclude", table_name_pattern: "tmp_*" },
  ],
  created_at: "2026-11-01T09:00:00Z",
  updated_at: "2026-11-05T09:00:00Z",
};

describe("discoveryPolicyDraft", () => {
  it("turns a policy into a draft and back into the same content", () => {
    const draft = draftFromPolicy(POLICY);
    expect(draft.version).toBe(2);
    expect(draft.description).toBe(POLICY.description);
    expect(draft.rules.map((rule) => [rule.action, rule.tableNamePattern])).toEqual([
      ["include", "orders*"],
      ["exclude", "tmp_*"],
    ]);
    expect(updateRequest(draft)).toEqual({
      version: 2,
      description: POLICY.description,
      rules: POLICY.rules,
    });
  });

  it("gives every rule of a policy its own key", () => {
    const twice = { ...POLICY, rules: [POLICY.rules[0]!, POLICY.rules[0]!] };
    const keys = draftFromPolicy(twice).rules.map((rule) => rule.key);
    expect(new Set(keys).size).toBe(2);
  });

  it("maps the rows in the draft's order, with its description", () => {
    const draft = draftFromPolicy(POLICY);
    const request = updateRequest({ ...draft, description: "Only orders", rules: [draft.rules[1]!, draft.rules[0]!] });
    expect(request).toEqual({
      version: 2,
      description: "Only orders",
      rules: [
        { action: "exclude", table_name_pattern: "tmp_*" },
        { action: "include", table_name_pattern: "orders*" },
      ],
    });
  });

  it("starts a new rule as include with an empty pattern", () => {
    expect(newRuleDraft("new-7")).toEqual({ key: "new-7", action: "include", tableNamePattern: "" });
  });

  it("is complete only with at least one rule and every pattern filled in", () => {
    const draft = draftFromPolicy(POLICY);
    expect(isDraftComplete(draft)).toBe(true);
    expect(isDraftComplete({ ...draft, rules: [] })).toBe(false);
    expect(isDraftComplete({ ...draft, rules: [...draft.rules, newRuleDraft("new-1")] })).toBe(false);
    expect(isDraftComplete({ ...draft, rules: [{ ...newRuleDraft("new-1"), tableNamePattern: "  " }] })).toBe(false);
    expect(isDraftComplete({ ...draft, rules: [{ ...newRuleDraft("new-1"), tableNamePattern: "x" }] })).toBe(true);
  });

  it("moves a rule one place up or down and leaves the ends alone", () => {
    const rules = ["a", "b", "c"].map((key) => ({ ...newRuleDraft(key), tableNamePattern: key }));
    expect(movedRule(rules, "c", -1).map((rule) => rule.key)).toEqual(["a", "c", "b"]);
    expect(movedRule(rules, "a", 1).map((rule) => rule.key)).toEqual(["b", "a", "c"]);
    expect(movedRule(rules, "a", -1)).toBe(rules);
    expect(movedRule(rules, "c", 1)).toBe(rules);
    expect(movedRule(rules, "missing", 1)).toBe(rules);
  });

  it("labels the actions Include and Exclude", () => {
    expect(actionLabel("include")).toBe("Include");
    expect(actionLabel("exclude")).toBe("Exclude");
  });

  it("reads a rule in one line, action first", () => {
    const [orders, temporary] = draftFromPolicy(POLICY).rules;
    expect(ruleText(orders!)).toBe("Include orders*");
    expect(ruleText(temporary!)).toBe("Exclude tmp_*");
  });
});
