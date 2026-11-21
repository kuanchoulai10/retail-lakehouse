import { describe, expect, it } from "vitest";
import { discoveryPoliciesPath, discoveryPolicyPath, discoveryPolicyVersionPath } from "./discoveryPolicyPaths";

describe("discoveryPolicyPaths", () => {
  it("puts the list at /discovery-policies", () => {
    expect(discoveryPoliciesPath()).toBe("/discovery-policies");
  });

  it("names a policy's page by its name", () => {
    expect(discoveryPolicyPath("sales-tables")).toBe("/discovery-policies/sales-tables");
  });

  it("names a kept version by the policy's name and the version number", () => {
    expect(discoveryPolicyVersionPath("sales-tables", 2)).toBe("/discovery-policies/sales-tables/versions/2");
  });

  it("encodes the name as one path segment", () => {
    expect(discoveryPolicyPath("a/b c")).toBe("/discovery-policies/a%2Fb%20c");
    expect(discoveryPolicyVersionPath("a/b c", 1)).toBe("/discovery-policies/a%2Fb%20c/versions/1");
  });
});
