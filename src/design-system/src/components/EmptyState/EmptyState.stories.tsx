import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { expectNoHorizontalPageScroll } from "../../stories/assertions";
import { Button } from "../Button/Button";
import { EmptyState } from "./EmptyState";

const meta = {
  title: "Components/EmptyState",
  component: EmptyState,
  args: { title: "No tables yet" },
  parameters: {
    docs: {
      description: {
        component:
          "No Serendie counterpart. Centred title, optional description and one action. " +
          "Sizes are the same in both window classes.",
      },
    },
  },
} satisfies Meta<typeof EmptyState>;

export default meta;

type Story = StoryObj<typeof meta>;

export const TitleOnly: Story = {
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("No tables yet")).toBeVisible();
  },
};

export const Full: Story = {
  args: {
    description: "Tables appear here once a discovery rule matches them.",
    action: <Button>Add rule</Button>,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText(/discovery rule/)).toBeVisible();
    await expect(canvas.getByRole("button", { name: "Add rule" })).toBeVisible();
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  args: {
    description: "Tables appear here once a discovery rule matches them.",
    action: <Button>Add rule</Button>,
  },
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
