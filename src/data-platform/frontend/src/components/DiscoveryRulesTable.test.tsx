import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { DiscoveryRuleDraft } from "@/lib/discoveryPolicyDraft";
import { DiscoveryRulesTable } from "./DiscoveryRulesTable";

const RULES: DiscoveryRuleDraft[] = [
  { key: "a", action: "include", tableNamePattern: "orders*" },
  { key: "b", action: "exclude", tableNamePattern: "tmp_*" },
];

function table(): HTMLElement {
  return screen.getByRole("table", { name: "Discovery rules, read top to bottom" });
}

describe("DiscoveryRulesTable", () => {
  it("lists each rule by position, action and table name pattern", () => {
    render(<DiscoveryRulesTable rules={RULES} />);
    const headers = within(table()).getAllByRole("columnheader").map((header) => header.textContent);
    expect(headers).toEqual(["#", "Action", "Table name pattern"]);
    const [first, second] = within(table()).getAllByRole("row").slice(1);
    expect(within(first!).getAllByRole("cell").map((cell) => cell.textContent)).toEqual(["1", "Include", "orders*"]);
    expect(within(second!).getAllByRole("cell").map((cell) => cell.textContent)).toEqual(["2", "Exclude", "tmp_*"]);
    expect(within(first!).getByText("orders*")).toHaveClass("font-mono");
    expect(within(table()).queryByRole("button")).not.toBeInTheDocument();
  });

  it("says when there are no rules", () => {
    render(<DiscoveryRulesTable rules={[]} emptyState="No rules." />);
    expect(screen.getByText("No rules.")).toBeInTheDocument();
  });
});
