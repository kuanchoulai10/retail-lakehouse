import { describe, expect, it } from "vitest";
import { partitionChangeSummary, partitionChangeTag } from "./partitionChangeText";

describe("partitionChangeSummary", () => {
  it("lists the non-zero kinds in enum order", () => {
    expect(partitionChangeSummary({ added: 1, removed: 2, renamed: 0, transform_changed: 3 })).toBe(
      "+1 added · −2 removed · 3 transform changed",
    );
  });

  it("says a first version has no earlier one and an unchanged one has no changes", () => {
    expect(partitionChangeSummary(null)).toBe("First version");
    expect(partitionChangeSummary({ added: 0, removed: 0, renamed: 0, transform_changed: 0 })).toBe("No changes");
  });
});

describe("partitionChangeTag", () => {
  it("names each change that tags a changed row", () => {
    expect((["renamed", "transform_changed"] as const).map(partitionChangeTag)).toEqual([
      "Renamed",
      "Transform changed",
    ]);
  });
});
