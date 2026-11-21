import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { DiscoveryRuleDraft } from "@/lib/discoveryPolicyDraft";
import { DiscoveryRulesTable } from "./DiscoveryRulesTable";

const RULES: DiscoveryRuleDraft[] = [
  { key: "a", id: "dr-a", outcome: "manage", namespaces: ["sales", "sales.*"], tableNames: ["orders*"] },
  { key: "b", id: "dr-b", outcome: "unmanage", namespaces: [], tableNames: ["tmp_*"] },
];

function table(): HTMLElement {
  return screen.getByRole("table", { name: "Discovery rules, read top to bottom" });
}

function rows(): HTMLElement[] {
  return within(table()).getAllByRole("row").slice(1);
}

function actions() {
  return { move: vi.fn(), edit: vi.fn(), remove: vi.fn() };
}

describe("DiscoveryRulesTable", () => {
  it("lists each rule by position, outcome and globs", () => {
    render(<DiscoveryRulesTable rules={RULES} readOnly />);
    const headers = within(table()).getAllByRole("columnheader").map((header) => header.textContent);
    expect(headers).toEqual(["#", "Outcome", "Namespace", "Table name"]);
    const [first, second] = rows();
    expect(within(first!).getAllByRole("cell").map((cell) => cell.textContent)).toEqual([
      "1",
      "Manage",
      "salessales.*",
      "orders*",
    ]);
    expect(within(second!).getAllByRole("cell")[1]).toHaveTextContent("Do not manage");
    expect(within(second!).getAllByRole("cell")[2]).toHaveTextContent("—");
    expect(within(first!).getByText("sales.*")).toHaveClass("font-mono");
  });

  it("has no row actions when read only", () => {
    render(<DiscoveryRulesTable rules={RULES} readOnly />);
    expect(within(table()).queryByRole("button")).not.toBeInTheDocument();
  });

  it("moves, edits and deletes a rule through its row actions", async () => {
    const user = userEvent.setup();
    const handlers = actions();
    render(<DiscoveryRulesTable rules={RULES} readOnly={false} actions={handlers} />);
    expect(screen.getByRole("button", { name: "Move rule 1 up" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Move rule 2 down" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Move rule 2 up" }));
    expect(handlers.move).toHaveBeenCalledWith(RULES[1], -1);
    await user.click(screen.getByRole("button", { name: "Move rule 1 down" }));
    expect(handlers.move).toHaveBeenCalledWith(RULES[0], 1);
    await user.click(screen.getByRole("button", { name: "Edit rule 2" }));
    expect(handlers.edit).toHaveBeenCalledWith(RULES[1]);
    await user.click(screen.getByRole("button", { name: "Delete rule 1" }));
    expect(handlers.remove).toHaveBeenCalledWith(RULES[0]);
  });

  it("shows a rule's hints under its conditions", () => {
    render(<DiscoveryRulesTable rules={RULES} readOnly hints={{ a: ["On a table, a rule either always or never matches it."] }} />);
    const [first, second] = rows();
    expect(within(first!).getByText("On a table, a rule either always or never matches it.")).toBeInTheDocument();
    expect(within(second!).queryByText(/On a table/)).not.toBeInTheDocument();
  });

  // A click landing while the page re-renders (say, when the attachments load) must not be lost.
  it("keeps its row controls when re-rendered with the same actions and new hints", () => {
    const handlers = actions();
    const { rerender } = render(<DiscoveryRulesTable rules={RULES} readOnly={false} actions={handlers} />);
    const edit = screen.getByRole("button", { name: "Edit rule 1" });
    rerender(<DiscoveryRulesTable rules={[...RULES]} readOnly={false} actions={handlers} hints={{ a: ["A hint."] }} />);
    expect(screen.getByRole("button", { name: "Edit rule 1" })).toBe(edit);
    expect(screen.getByText("A hint.")).toBeInTheDocument();
  });

  it("says when there are no rules", () => {
    render(<DiscoveryRulesTable rules={[]} readOnly emptyState="No rules." />);
    expect(screen.getByText("No rules.")).toBeInTheDocument();
  });
});
