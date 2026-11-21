import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import { draftFromPolicy } from "@/lib/discoveryPolicyDraft";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { PHONE } from "@/stories/phone";
import { SALES_TABLES } from "@/stories/storyData";
import { DiscoveryRulesTable } from "./DiscoveryRulesTable";

const RULES = draftFromPolicy(SALES_TABLES).rules;

const meta = {
  title: "Components/Discovery rules table",
  component: DiscoveryRulesTable,
  args: { rules: RULES, readOnly: true },
} satisfies Meta<typeof DiscoveryRulesTable>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ReadOnly: Story = {
  play: async ({ canvasElement }) => {
    const table = within(canvasElement).getByRole("table", { name: "Discovery rules, read top to bottom" });
    await expect(within(table).getByText("Do not manage")).toBeVisible();
    await expect(within(table).getByText("sales.*")).toBeVisible();
    await expect(within(table).queryByRole("button")).toBeNull();
  },
};

// From a row's first enabled action, Tab goes through Edit and Delete to the next row's actions.
export const Editable: Story = {
  args: { readOnly: false, actions: { move: fn(), edit: fn(), remove: fn() } },
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("button", { name: "Move rule 1 up" })).toBeDisabled();
    canvas.getByRole("button", { name: "Move rule 1 down" }).focus();
    await userEvent.tab();
    await expect(canvas.getByRole("button", { name: "Edit rule 1" })).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await expect(args.actions?.edit).toHaveBeenCalledWith(RULES[0]);
    await userEvent.tab();
    await expect(canvas.getByRole("button", { name: "Delete rule 1" })).toHaveFocus();
    await userEvent.tab();
    await expect(canvas.getByRole("button", { name: "Move rule 2 up" })).toHaveFocus();
    await userEvent.keyboard(" ");
    await expect(args.actions?.move).toHaveBeenCalledWith(RULES[1], -1);
  },
};

export const WithHints: Story = {
  args: {
    hints: { [RULES[0]!.key]: ["Attached to namespace iceberg.sales: a namespace glob only tells its child namespaces apart."] },
  },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText(/a namespace glob only tells its child namespaces apart/)).toBeVisible();
  },
};

export const Empty: Story = {
  args: { rules: [] },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("No rules.")).toBeVisible();
  },
};

export const Phone: Story = {
  globals: PHONE,
  args: { readOnly: false, actions: { move: fn(), edit: fn(), remove: fn() } },
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
