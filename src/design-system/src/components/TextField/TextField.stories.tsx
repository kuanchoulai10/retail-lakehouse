import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { expectFocusRing, expectNoHorizontalPageScroll } from "../../stories/assertions";
import { TextField } from "./TextField";

const meta = {
  title: "Components/TextField",
  component: TextField,
  args: { label: "Table name", description: "Fully qualified, for example sales.orders" },
  decorators: [
    (Story) => (
      <div className="max-w-sm p-4">
        <Story />
      </div>
    ),
  ],
  parameters: {
    docs: {
      description: {
        component:
          "Expanded departs from Serendie: the input is 36px high (Serendie 48px) and stays " +
          "44px below 768px and under a coarse pointer.",
      },
    },
  },
} satisfies Meta<typeof TextField>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const input = canvas.getByLabelText("Table name");
    await userEvent.tab();
    await expectFocusRing(input);
    await userEvent.tab({ shift: true });
    await expect(input).not.toHaveFocus();
    await userEvent.click(canvas.getByText("Table name"));
    await expect(input).toHaveFocus();
    await userEvent.keyboard("sales.orders");
    await expect(input).toHaveValue("sales.orders");
    await expect(input).toHaveAccessibleDescription("Fully qualified, for example sales.orders");
  },
};

export const Invalid: Story = {
  args: { invalid: true, invalidMessage: "Table name must include a namespace" },
  play: async ({ canvasElement }) => {
    const input = within(canvasElement).getByLabelText("Table name");
    await expect(input).toHaveAttribute("aria-invalid", "true");
    const message = within(canvasElement).getByText("Table name must include a namespace");
    await expect(message.closest("[aria-live]")).toHaveAttribute("aria-live", "polite");
    await expect(input).toHaveAccessibleDescription(
      "Fully qualified, for example sales.orders Table name must include a namespace",
    );
  },
};

export const Required: Story = {
  args: { required: true },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByLabelText(/Table name/)).toBeRequired();
  },
};

export const Disabled: Story = {
  args: { disabled: true },
  play: async ({ canvasElement }) => {
    const input = within(canvasElement).getByLabelText("Table name");
    await expect(input).toBeDisabled();
    await userEvent.tab();
    await expect(input).not.toHaveFocus();
  },
};

export const Touch: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  play: async ({ canvasElement }) => {
    const input = within(canvasElement).getByLabelText("Table name");
    await expect(input.getBoundingClientRect().height).toBe(44);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const Desktop: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  play: async ({ canvasElement }) => {
    const input = within(canvasElement).getByLabelText("Table name");
    await expect(input.getBoundingClientRect().height).toBe(36);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
