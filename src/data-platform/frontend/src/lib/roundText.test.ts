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
    expect(usedText({ used_gb_hours: 0.04, budget_gb_hours: 0.05 })).toBe("0.04 of 0.05 (80%)");
  });

  it("shows a first pick larger than the budget above 100%", () => {
    expect(usedText({ used_gb_hours: 0.12, budget_gb_hours: 0.05 })).toBe("0.12 of 0.05 (240%)");
  });

  it("shows only the use for a round without a budget", () => {
    expect(usedText({ used_gb_hours: 0, budget_gb_hours: 0 })).toBe("0.00");
  });
});

describe("candidatesPathOf", () => {
  it("links a pick's table to its Candidates tab", () => {
    expect(candidatesPathOf("iceberg.retail.orders")).toBe("/catalogs/iceberg/namespaces/retail/tables/orders/candidates");
  });

  it("has no link for a table no longer known", () => {
    expect(candidatesPathOf(null)).toBeNull();
  });
});
