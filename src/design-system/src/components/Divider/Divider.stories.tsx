import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { expectNoHorizontalPageScroll } from "../../stories/assertions";
import { Divider } from "./Divider";

const meta = {
  title: "Components/Divider",
  component: Divider,
  parameters: {
    docs: {
      description: {
        component:
          "Expanded departs from Serendie: a single 1px outline-dim line, no colour variants.",
      },
    },
  },
} satisfies Meta<typeof Divider>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Horizontal: Story = {
  render: (args) => (
    <div className="p-4 text-on-surface">
      <p>Above</p>
      <Divider {...args} />
      <p>Below</p>
    </div>
  ),
  play: async ({ canvasElement }) => {
    const root = canvasElement.querySelector("[data-orientation='horizontal']");
    await expect(root).not.toBeNull();
    await expect((root as HTMLElement).getBoundingClientRect().height).toBe(1);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const Vertical: Story = {
  args: { orientation: "vertical" },
  render: (args) => (
    <div className="flex h-10 items-center gap-2 p-4 text-on-surface">
      <span>Left</span>
      <Divider {...args} />
      <span>Right</span>
    </div>
  ),
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("Right")).toBeVisible();
    await expect(canvasElement.querySelector("[data-orientation='vertical']")).not.toBeNull();
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  render: (args) => (
    <div className="p-4">
      <Divider {...args} />
    </div>
  ),
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
