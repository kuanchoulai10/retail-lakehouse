import { describe, expect, it } from "vitest";
import { schemaChangeSummary, schemaChangeTag } from "./schemaChangeText";

const NONE = { added: 0, removed: 0, renamed: 0, type_changed: 0, nullability_changed: 0, doc_changed: 0 };

describe("schemaChangeSummary", () => {
  it("summarises a version's changes", () => {
    expect(schemaChangeSummary({ ...NONE, added: 1, type_changed: 1 })).toBe("+1 added · 1 type changed");
  });

  it("lists every kind in enum order", () => {
    expect(
      schemaChangeSummary({ added: 5, removed: 2, renamed: 3, type_changed: 4, nullability_changed: 6, doc_changed: 7 }),
    ).toBe("+5 added · −2 removed · 3 renamed · 4 type changed · 6 nullability changed · 7 doc changed");
  });

  it("says a first version has no earlier one and an unchanged one has no changes", () => {
    expect(schemaChangeSummary(null)).toBe("First version");
    expect(schemaChangeSummary(NONE)).toBe("No changes");
  });
});

describe("schemaChangeTag", () => {
  it("names each change that tags a changed row", () => {
    expect(
      (["renamed", "type_changed", "nullability_changed", "doc_changed"] as const).map(schemaChangeTag),
    ).toEqual(["Renamed", "Type changed", "Nullability changed", "Doc changed"]);
  });
});
