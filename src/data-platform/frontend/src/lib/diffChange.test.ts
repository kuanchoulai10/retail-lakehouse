import { describe, expect, it } from "vitest";
import { diffChange } from "./diffChange";

const tag = (kind: "renamed" | "type_changed") => (kind === "renamed" ? "Renamed" : "Type changed");

describe("diffChange", () => {
  it("reads an added or a removed row as such, with no tag", () => {
    expect(diffChange(["added"], tag)).toEqual({ change: "added", tags: [] });
    expect(diffChange(["removed"], tag)).toEqual({ change: "removed", tags: [] });
  });

  it("reads any other change as changed, tagging each kind in order", () => {
    expect(diffChange(["renamed", "type_changed"], tag)).toEqual({ change: "changed", tags: ["Renamed", "Type changed"] });
  });

  it("reads no change as unchanged", () => {
    expect(diffChange([], tag)).toEqual({ change: "unchanged", tags: [] });
  });
});
