import { describe, expect, it } from "vitest";
import { detachPlace } from "./detachPlace";

describe("detachPlace", () => {
  it("names a place by its type and its whole path, as the detach query takes them", () => {
    expect(detachPlace({ type: "table", path: ["iceberg", "retail", "orders"] })).toEqual({
      target_type: "table",
      path: ["iceberg", "retail", "orders"],
    });
    expect(detachPlace({ type: "catalog", path: ["iceberg"] })).toEqual({ target_type: "catalog", path: ["iceberg"] });
  });
});
