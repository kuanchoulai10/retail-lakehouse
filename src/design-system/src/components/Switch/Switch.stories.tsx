import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import { expectFocusRing, expectNoHorizontalPageScroll } from "../../stories/assertions";
import { Switch } from "./Switch";

const meta = {
  title: "Components/Switch",
  component: Switch,
  args: { label: "Pause scheduling", onCheckedChange: fn() },
  decorators: [
    (Story) => (
      <div className="p-4">
        <Story />
      </div>
    ),
  ],
  parameters: {
    docs: {
      description: {
        component:
          "Expanded departs from Serendie: the whole row is 36px high around a 56 x 32px track; " +
          "the row stays 44px below 768px and under a coarse pointer.",
      },
    },
  },
} satisfies Meta<typeof Switch>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    const box = canvas.getByRole("switch", { name: "Pause scheduling" });
    await userEvent.tab();
    await expectFocusRing(box);
    await userEvent.keyboard(" ");
    await expect(args.onCheckedChange).toHaveBeenLastCalledWith(true);
    await expect(box).toBeChecked();
    await userEvent.keyboard(" ");
    await expect(args.onCheckedChange).toHaveBeenLastCalledWith(false);
    await userEvent.click(canvas.getByText("Pause scheduling"));
    await expect(box).toBeChecked();
  },
};

export const Checked: Story = {
  args: { checked: true },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("switch")).toBeChecked();
  },
};

export const Disabled: Story = {
  args: { disabled: true },
  play: async ({ canvasElement, args }) => {
    const box = within(canvasElement).getByRole("switch");
    await userEvent.click(box);
    await userEvent.tab();
    await expect(box).not.toHaveFocus();
    await expect(args.onCheckedChange).not.toHaveBeenCalled();
  },
};

export const Touch: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  play: async ({ canvasElement }) => {
    const row = within(canvasElement).getByRole("switch").parentElement as HTMLElement;
    await expect(row.getBoundingClientRect().height).toBeGreaterThanOrEqual(44);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
