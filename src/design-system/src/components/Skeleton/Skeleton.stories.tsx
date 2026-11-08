import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect } from "storybook/test";
import { expectNoHorizontalPageScroll } from "../../stories/assertions";
import { Skeleton } from "./Skeleton";

const meta = {
  title: "Components/Skeleton",
  component: Skeleton,
  args: { className: "h-6 w-48" },
  parameters: {
    docs: {
      description: {
        component:
          "No Serendie counterpart. Decorative placeholder, hidden from assistive technology; " +
          "the pulse stops under reduced motion.",
      },
    },
  },
} satisfies Meta<typeof Skeleton>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Line: Story = {
  play: async ({ canvasElement }) => {
    const skeleton = canvasElement.querySelector("[aria-hidden='true']");
    await expect(skeleton).not.toBeNull();
  },
};

export const Block: Story = { args: { className: "h-24 w-full" } };

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  args: { className: "h-24 w-full" },
  play: async ({ canvasElement }) => expectNoHorizontalPageScroll(canvasElement),
};
