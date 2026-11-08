import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { expectNoHorizontalPageScroll } from "../../stories/assertions";
import { StatusBadge } from "./StatusBadge";

const meta = {
  title: "Components/StatusBadge",
  component: StatusBadge,
  args: { status: "neutral", children: "Pending" },
  parameters: {
    docs: {
      description: {
        component:
          "No Serendie counterpart. Uses the container and on-container token pairs; the status " +
          "is always carried by the text, never by colour alone.",
      },
    },
  },
} satisfies Meta<typeof StatusBadge>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Positive: Story = { args: { status: "positive", children: "Succeeded" } };

export const Notice: Story = { args: { status: "notice", children: "Running" } };

export const Negative: Story = { args: { status: "negative", children: "Failed" } };

export const Neutral: Story = {
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("Pending")).toBeVisible();
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  render: () => (
    <div className="flex flex-wrap gap-2 p-4">
      <StatusBadge status="positive">Succeeded</StatusBadge>
      <StatusBadge status="notice">Running</StatusBadge>
      <StatusBadge status="negative">Failed</StatusBadge>
      <StatusBadge status="neutral">Pending</StatusBadge>
    </div>
  ),
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
