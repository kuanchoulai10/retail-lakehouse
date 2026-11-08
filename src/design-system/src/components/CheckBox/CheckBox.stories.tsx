import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import { expectFocusRing, expectNoHorizontalPageScroll } from "../../stories/assertions";
import { CheckBox } from "./CheckBox";

const meta = {
  title: "Components/CheckBox",
  component: CheckBox,
  args: { label: "Compact data files", onCheckedChange: fn() },
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
          "Expanded departs from Serendie: the whole row is 36px high with a 24px box " +
          "(Serendie 48px); the row stays 44px below 768px and under a coarse pointer.",
      },
    },
  },
} satisfies Meta<typeof CheckBox>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    const box = canvas.getByRole("checkbox", { name: "Compact data files" });
    await userEvent.tab();
    await expectFocusRing(box);
    await userEvent.keyboard(" ");
    await expect(args.onCheckedChange).toHaveBeenLastCalledWith(true);
    await expect(box).toBeChecked();
    await userEvent.keyboard(" ");
    await expect(args.onCheckedChange).toHaveBeenLastCalledWith(false);
    await userEvent.click(canvas.getByText("Compact data files"));
    await expect(box).toBeChecked();
  },
};

export const Checked: Story = {
  args: { checked: true },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("checkbox")).toBeChecked();
  },
};

export const Disabled: Story = {
  args: { disabled: true },
  play: async ({ canvasElement, args }) => {
    const box = within(canvasElement).getByRole("checkbox");
    await userEvent.click(box);
    await userEvent.tab();
    await expect(box).not.toHaveFocus();
    await expect(args.onCheckedChange).not.toHaveBeenCalled();
  },
};

export const Touch: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  play: async ({ canvasElement }) => {
    const row = within(canvasElement).getByRole("checkbox").parentElement as HTMLElement;
    await expect(row.getBoundingClientRect().height).toBeGreaterThanOrEqual(44);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
