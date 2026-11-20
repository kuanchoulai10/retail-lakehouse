import { describe, expect, it } from "vitest";
import { priorityText } from "./priorityText";

describe("priorityText", () => {
  it("is the priority itself", () => {
    expect(priorityText("P2")).toBe("P2");
    expect(priorityText("P0")).toBe("P0");
  });

  it("shows a priority it does not know as it is", () => {
    expect(priorityText("P9")).toBe("P9");
  });
});
