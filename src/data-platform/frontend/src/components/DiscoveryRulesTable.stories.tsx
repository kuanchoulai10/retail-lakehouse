import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { draftFromPolicy } from "@/lib/discoveryPolicyDraft";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { PHONE } from "@/stories/phone";
import { SALES_TABLES } from "@/stories/storyData";
import { DiscoveryRulesTable } from "./DiscoveryRulesTable";

const RULES = draftFromPolicy(SALES_TABLES).rules;

const meta = {
  title: "Components/Discovery rules table",
  component: DiscoveryRulesTable,
  args: { rules: RULES },
} satisfies Meta<typeof DiscoveryRulesTable>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ReadOnly: Story = {
  play: async ({ canvasElement }) => {
    const table = within(canvasElement).getByRole("table", { name: "Discovery rules, read top to bottom" });
    await expect(within(table).getAllByText("Exclude")).toHaveLength(2);
    await expect(within(table).getByText("tmp_*")).toBeVisible();
    await expect(within(table).queryByRole("button")).toBeNull();
    await expect(within(table).queryByRole("textbox")).toBeNull();
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
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
