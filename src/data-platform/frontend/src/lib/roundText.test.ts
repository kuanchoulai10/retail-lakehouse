import { describe, expect, it } from "vitest";
import { candidatesPathOf, skipReasonText, usedText } from "./roundText";

describe("skipReasonText", () => {
  it("says why a candidate was skipped", () => {
    expect(skipReasonText("budget_used")).toBe("Budget used");
    expect(skipReasonText("table_share_used")).toBe("Table's share used");
    expect(skipReasonText("table_busy")).toBe("Table busy");
  });

  it("reads an unknown reason in words", () => {
    expect(skipReasonText("table_paused")).toBe("table paused");
  });
});

describe("usedText", () => {
  it("says how much of the budget the picks use", () => {
    expect(usedText({ used_gb_hours: 0.04, budget_gb_hours: 0.05 })).toBe("0.04 (80%)");
  });

  it("shows a first pick larger than the budget above 100%", () => {
    expect(usedText({ used_gb_hours: 0.12, budget_gb_hours: 0.05 })).toBe("0.12 (240%)");
  });

  it("shows a use too small to round as below one hundredth", () => {
    expect(usedText({ used_gb_hours: 0.00044, budget_gb_hours: 0.0005 })).toBe("< 0.01 (88%)");
  });

  it("shows only the use for a round without a budget", () => {
    expect(usedText({ used_gb_hours: 0, budget_gb_hours: 0 })).toBe("0.00");
  });
});

describe("candidatesPathOf", () => {
  it("links a pick's table to its Candidates tab", () => {
    expect(candidatesPathOf({ catalog: "iceberg", namespace: ["retail"], name: "orders" })).toBe(
      "/catalogs/iceberg/namespaces/retail/tables/orders/candidates",
    );
  });

  it("keeps a namespace part with a dot in it one part", () => {
    expect(candidatesPathOf({ catalog: "ice.berg", namespace: ["sales.eu", "daily"], name: "orders" })).toBe(
      "/catalogs/ice.berg/namespaces/sales.eu%1Fdaily/tables/orders/candidates",
    );
  });

  it("has no link for a table no longer known", () => {
    expect(candidatesPathOf(null)).toBeNull();
  });
});
