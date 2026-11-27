import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { expect, screen, userEvent, waitFor, within } from "storybook/test";
import { draftFromPolicy, type DiscoveryRuleDraft } from "@/lib/discoveryPolicyDraft";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { PHONE } from "@/stories/phone";
import { SALES_TABLES } from "@/stories/storyData";
import { DiscoveryRuleEditor } from "./DiscoveryRuleEditor";

const RULES = draftFromPolicy(SALES_TABLES).rules;

// The page holds the draft; the story holds it here, so every edit shows.
function Stateful({ initial, focusKey }: { initial: DiscoveryRuleDraft[]; focusKey?: string | null }) {
  const [rules, setRules] = useState(initial);
  return <DiscoveryRuleEditor rules={rules} onChange={(edit) => setRules(edit)} focusKey={focusKey} />;
}

const meta = {
  title: "Components/Discovery rule editor",
  component: Stateful,
  args: { initial: RULES },
} satisfies Meta<typeof Stateful>;

export default meta;
type Story = StoryObj<typeof meta>;

function pattern(canvasElement: HTMLElement, position: number): HTMLElement {
  return within(canvasElement).getByRole("textbox", { name: `Table name pattern of rule ${position}` });
}

export const Rules: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const table = canvas.getByRole("table", { name: "Discovery rules, read top to bottom" });
    await expect(within(table).getByRole("combobox", { name: "Action of rule 1" })).toHaveTextContent("Include");
    await expect(within(table).getByRole("combobox", { name: "Action of rule 2" })).toHaveTextContent("Exclude");
    await expect(pattern(canvasElement, 2)).toHaveValue("tmp_*");
  },
};

export const Move: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("button", { name: "Move rule 1 up" })).toBeDisabled();
    await userEvent.click(canvas.getByRole("button", { name: "Move rule 3 up" }));
    await expect(pattern(canvasElement, 2)).toHaveValue("staging_*");
    await expect(pattern(canvasElement, 3)).toHaveValue("tmp_*");
  },
};

// Tab goes through a row's action, its pattern, then its buttons, and on to the next row; the action
// is picked with the arrow keys and the pattern keeps focus while it is typed in.
export const Keyboard: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const action = canvas.getByRole("combobox", { name: "Action of rule 1" });
    action.focus();
    await userEvent.keyboard("{Enter}");
    await screen.findByRole("listbox");
    await userEvent.keyboard("{ArrowDown}{Enter}");
    await waitFor(() => expect(action).toHaveTextContent("Exclude"));
    await expect(action).toHaveFocus();
    await userEvent.tab();
    await expect(pattern(canvasElement, 1)).toHaveFocus();
    await userEvent.keyboard("{Backspace}s");
    await expect(pattern(canvasElement, 1)).toHaveValue("s");
    await expect(pattern(canvasElement, 1)).toHaveFocus();
    await userEvent.tab();
    await expect(canvas.getByRole("button", { name: "Move rule 1 down" })).toHaveFocus();
    await userEvent.tab();
    await expect(canvas.getByRole("button", { name: "Delete rule 1" })).toHaveFocus();
    await userEvent.tab();
    await expect(canvas.getByRole("combobox", { name: "Action of rule 2" })).toHaveFocus();
  },
};

export const Delete: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Delete rule 1" }));
    await expect(pattern(canvasElement, 1)).toHaveValue("tmp_*");
  },
};

export const FocusesNewRule: Story = {
  args: { initial: [...RULES, { key: "new-1", action: "include", tableNamePattern: "" }], focusKey: "new-1" },
  play: async ({ canvasElement }) => {
    await waitFor(() => expect(pattern(canvasElement, 4)).toHaveFocus());
  },
};

export const Empty: Story = {
  args: { initial: [] },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("No rules. A policy needs at least one.")).toBeVisible();
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
