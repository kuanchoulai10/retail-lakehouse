import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import { SerendieSymbolTrash } from "../../icons";
import { expectNoHorizontalPageScroll } from "../../stories/assertions";
import { IconButton } from "./IconButton";

const meta = {
  title: "Components/IconButton",
  component: IconButton,
  args: {
    icon: <SerendieSymbolTrash aria-hidden="true" />,
    "aria-label": "Delete rule",
    onClick: fn(),
  },
  parameters: {
    docs: {
      description: {
        component:
          "Expanded departs from Serendie: one 44px touch size instead of the 40/52/68px scale.",
      },
    },
  },
} satisfies Meta<typeof IconButton>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Filled: Story = {
  play: async ({ canvasElement, args }) => {
    const button = within(canvasElement).getByRole("button", { name: "Delete rule" });
    await expect(button).toHaveAccessibleName(args["aria-label"]);
    await userEvent.tab();
    await expect(button).toHaveFocus();
    await expect(getComputedStyle(button).outlineWidth).not.toBe("0px");
    await userEvent.keyboard("{Enter}");
    await expect(args.onClick).toHaveBeenCalledTimes(1);
    await userEvent.keyboard(" ");
    await expect(args.onClick).toHaveBeenCalledTimes(2);
    await expect(button.getBoundingClientRect().height).toBe(44);
  },
};

export const Outlined: Story = { args: { styleType: "outlined" } };

export const Ghost: Story = { args: { styleType: "ghost" } };

export const Rectangle: Story = { args: { shape: "rectangle", styleType: "outlined" } };

export const Disabled: Story = {
  args: { disabled: true },
  play: async ({ canvasElement, args }) => {
    await userEvent.click(within(canvasElement).getByRole("button", { name: "Delete rule" }));
    await expect(args.onClick).not.toHaveBeenCalled();
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
