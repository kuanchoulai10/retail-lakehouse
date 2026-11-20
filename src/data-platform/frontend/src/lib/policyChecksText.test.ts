import { describe, expect, it } from "vitest";
import { policyChecksText } from "./policyChecksText";

describe("policyChecksText", () => {
  it("names the schedule alone when commits do not trigger a check", () => {
    expect(policyChecksText({ schedule: { every_seconds: 3600 }, catalog_commit: null })).toBe("Every 1 h");
    expect(policyChecksText({ schedule: { every_seconds: 3600 } })).toBe("Every 1 h");
  });

  it("adds the debounce after a commit", () => {
    expect(
      policyChecksText({ schedule: { every_seconds: 3600 }, catalog_commit: { debounce_seconds: 300 } }),
    ).toBe("Every 1 h, and 5 min after a commit");
  });

  it("says right after a commit when there is no debounce", () => {
    expect(policyChecksText({ schedule: { every_seconds: 300 }, catalog_commit: { debounce_seconds: 0 } })).toBe(
      "Every 5 min, and right after a commit",
    );
  });
});
