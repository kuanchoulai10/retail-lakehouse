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
          "Departs from Serendie's 52 x 32px track: the track is 36 x 20px from 768px and " +
          "44 x 24px below it, with a medium label, so a switch sits in a table row without " +
          "dominating it. The row stays 36px high expanded and 44px below 768px and under a " +
          "coarse pointer.",
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

export const Dense: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  play: async ({ canvasElement }) => {
    const box = within(canvasElement).getByRole("switch").getBoundingClientRect();
    await expect([box.width, box.height]).toEqual([36, 20]);
  },
};

export const Touch: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  play: async ({ canvasElement }) => {
    const box = within(canvasElement).getByRole("switch");
    const row = box.parentElement as HTMLElement;
    await expect(row.getBoundingClientRect().height).toBeGreaterThanOrEqual(44);
    await expect([box.getBoundingClientRect().width, box.getBoundingClientRect().height]).toEqual([44, 24]);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
