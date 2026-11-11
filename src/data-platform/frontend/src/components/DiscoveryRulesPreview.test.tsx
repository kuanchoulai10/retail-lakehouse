import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ApiError } from "@/api/apiError";
import type { PreviewTableDiscoveryRulesApiResponse } from "@/api/generated/model";
import type { DiscoveryRuleDraft } from "@/lib/discoveryRuleDraft";
import { DiscoveryRulesPreview } from "./DiscoveryRulesPreview";

function draft(overrides: Partial<DiscoveryRuleDraft>): DiscoveryRuleDraft {
  return { key: "k", id: null, priority: 10, action: "include", enabled: true, catalogs: ["*"], namespaces: ["*"], tables: ["*"], ...overrides };
}

const RULES = [
  draft({ key: "saved", id: "saved", priority: 10, action: "exclude" }),
  draft({ key: "new-1", id: null, priority: 20, action: "include" }),
];

const PREVIEW: PreviewTableDiscoveryRulesApiResponse = {
  tables: [
    { catalog: "iceberg", namespace: "retail", table: "orders", rule_id: "#1", managed: true },
    { catalog: "iceberg", namespace: "retail", table: "customers", rule_id: "#1", managed: true },
    { catalog: "iceberg", namespace: "tmp", table: "scratch", rule_id: "saved", managed: false },
    { catalog: "other", namespace: "x", table: "y", rule_id: null, managed: false },
  ],
  managed: 2,
  unmanaged: 2,
};

describe("DiscoveryRulesPreview", () => {
  it("groups tables by the rule that decides them, in rule order", () => {
    render(<DiscoveryRulesPreview rules={RULES} preview={PREVIEW} isFetching={false} error={null} />);
    expect(screen.getByText("2 managed, 2 unmanaged")).toBeInTheDocument();
    const groups = screen.getAllByRole("group");
    expect(groups.map((g) => g.getAttribute("aria-label"))).toEqual([
      "Priority 10, exclude: 1 table, unmanaged",
      "Priority 20, include (unsaved): 2 tables, managed",
      "No rule matches: 1 table, unmanaged",
    ]);
    expect(within(groups[1]!).getByText("retail.orders")).toBeInTheDocument();
  });

  it("names the catalog when the preview spans several", () => {
    render(<DiscoveryRulesPreview rules={RULES} preview={PREVIEW} isFetching={false} error={null} />);
    expect(screen.getByText("other")).toBeInTheDocument();
  });

  it("shows the API's message when the draft cannot be previewed", () => {
    render(<DiscoveryRulesPreview rules={RULES} preview={undefined} isFetching={false} error={new ApiError(422, "bad glob")} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Could not preview these rules: bad glob");
  });

  it("is busy while the preview loads", () => {
    render(<DiscoveryRulesPreview rules={RULES} preview={undefined} isFetching error={null} />);
    expect(screen.getByRole("region", { name: "Preview" })).toHaveAttribute("aria-busy", "true");
  });

  it("dims the tables it shows while a newer preview loads", () => {
    const { rerender } = render(<DiscoveryRulesPreview rules={RULES} preview={PREVIEW} isFetching={false} error={null} />);
    expect(screen.getByTestId("preview-results")).not.toHaveClass("opacity-60");
    rerender(<DiscoveryRulesPreview rules={RULES} preview={PREVIEW} isFetching error={null} />);
    expect(screen.getByTestId("preview-results")).toHaveClass("opacity-60");
  });
});
