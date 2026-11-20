import { describe, expect, it } from "vitest";
import { changeSummary, type ChangeSummaryPart } from "./changeSummary";

type Kind = "added" | "removed" | "renamed";

const PARTS: ChangeSummaryPart<Kind>[] = [
  ["added", (count) => `+${count} added`],
  ["removed", (count) => `−${count} removed`],
  ["renamed", (count) => `${count} renamed`],
];

describe("changeSummary", () => {
  it("joins the kinds with a count, in the order the parts give", () => {
    expect(changeSummary(PARTS, { renamed: 2, added: 1, removed: 0 })).toBe("+1 added · 2 renamed");
  });

  it("says a first version has no earlier one and an unchanged one has no changes", () => {
    expect(changeSummary(PARTS, null)).toBe("First version");
    expect(changeSummary(PARTS, { added: 0, removed: 0, renamed: 0 })).toBe("No changes");
  });
});
