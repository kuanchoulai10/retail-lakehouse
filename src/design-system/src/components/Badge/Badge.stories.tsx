import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { expectNoHorizontalPageScroll } from "../../stories/assertions";
import { Badge } from "./Badge";

const meta = {
  title: "Components/Badge",
  component: Badge,
  args: { children: "12" },
  parameters: {
    docs: {
      description: {
        component:
          "Neutral count or label chip. Expanded departs from Serendie: one size (24px min height) " +
          "and no colour variants; status colour lives in StatusBadge.",
      },
    },
  },
} satisfies Meta<typeof Badge>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Count: Story = {
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("12")).toBeVisible();
  },
};

export const Label: Story = { args: { children: "Iceberg v2" } };

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  play: async ({ canvasElement }) => expectNoHorizontalPageScroll(canvasElement),
};
