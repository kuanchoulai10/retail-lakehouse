import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import type { DiscoveryRuleDraft } from "@/lib/discoveryPolicyDraft";
import { DiscoveryRuleEditor } from "./DiscoveryRuleEditor";

const RULES: DiscoveryRuleDraft[] = [
  { key: "a", action: "include", tableNamePattern: "orders*" },
  { key: "b", action: "exclude", tableNamePattern: "tmp_*" },
];

// The page holds the draft; the editor hands it each change as an edit of the rules.
function Harness({ initial = RULES, focusKey = null }: { initial?: DiscoveryRuleDraft[]; focusKey?: string | null }) {
  const [rules, setRules] = useState(initial);
  return (
    <>
      <DiscoveryRuleEditor rules={rules} onChange={(edit) => setRules(edit)} focusKey={focusKey} />
      <output aria-label="Draft">{JSON.stringify(rules)}</output>
    </>
  );
}

function table(): HTMLElement {
  return screen.getByRole("table", { name: "Discovery rules, read top to bottom" });
}

function rows(): HTMLElement[] {
  return within(table()).getAllByRole("row").slice(1);
}

function draft(): DiscoveryRuleDraft[] {
  return JSON.parse(screen.getByRole("status", { name: "Draft" }).textContent ?? "[]") as DiscoveryRuleDraft[];
}

describe("DiscoveryRuleEditor", () => {
  it("has one row per rule, holding an action select and a pattern field", () => {
    render(<Harness />);
    const headers = within(table()).getAllByRole("columnheader").map((header) => header.textContent);
    expect(headers).toEqual(["#", "Action", "Table name pattern", "Actions"]);
    const [first, second] = rows();
    expect(within(first!).getByRole("combobox", { name: "Action of rule 1" })).toHaveTextContent("Include");
    expect(within(first!).getByRole("textbox", { name: "Table name pattern of rule 1" })).toHaveValue("orders*");
    expect(within(second!).getByRole("combobox", { name: "Action of rule 2" })).toHaveTextContent("Exclude");
    expect(within(second!).getByRole("textbox", { name: "Table name pattern of rule 2" })).toHaveValue("tmp_*");
    expect(within(first!).getByRole("textbox", { name: "Table name pattern of rule 1" })).toHaveClass("font-mono");
  });

  it("changes a rule's action and pattern in the draft", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole("combobox", { name: "Action of rule 1" }));
    await user.click(await screen.findByRole("option", { name: "Exclude" }));
    const pattern = screen.getByRole("textbox", { name: "Table name pattern of rule 2" });
    await user.clear(pattern);
    await user.type(pattern, "staging_*");
    expect(pattern).toHaveFocus();
    expect(draft()).toEqual([
      { key: "a", action: "exclude", tableNamePattern: "orders*" },
      { key: "b", action: "exclude", tableNamePattern: "staging_*" },
    ]);
  });

  it("moving a row reorders the rules, and the ends cannot move further", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    expect(screen.getByRole("button", { name: "Move rule 1 up" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Move rule 2 down" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Move rule 2 up" }));
    expect(draft().map((rule) => rule.key)).toEqual(["b", "a"]);
    expect(screen.getByRole("textbox", { name: "Table name pattern of rule 1" })).toHaveValue("tmp_*");
    await user.click(screen.getByRole("button", { name: "Move rule 1 down" }));
    expect(draft().map((rule) => rule.key)).toEqual(["a", "b"]);
  });

  it("deletes a row at once", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole("button", { name: "Delete rule 1" }));
    expect(draft()).toEqual([RULES[1]]);
    expect(rows()).toHaveLength(1);
  });

  it("says when there are no rules", () => {
    render(<Harness initial={[]} />);
    expect(screen.getByText("No rules. A policy needs at least one.")).toBeInTheDocument();
  });

  it("gives focus to the pattern field of the rule it is told to", async () => {
    render(<Harness focusKey="b" />);
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Table name pattern of rule 2" })).toHaveFocus());
  });
});
