import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { expectFocusRing, expectNoHorizontalPageScroll } from "../../stories/assertions";
import { TextArea } from "./TextArea";

const meta = {
  title: "Components/TextArea",
  component: TextArea,
  args: { label: "Notes", description: "Shown on the run history" },
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
          "Expanded departs from Serendie: the minimum height is one 36px control row " +
          "(Serendie 48px); it stays 44px below 768px and under a coarse pointer.",
      },
    },
  },
} satisfies Meta<typeof TextArea>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const textarea = canvas.getByLabelText("Notes");
    await userEvent.tab();
    await expectFocusRing(textarea);
    await userEvent.tab({ shift: true });
    await userEvent.click(canvas.getByText("Notes"));
    await expect(textarea).toHaveFocus();
    await userEvent.keyboard("first{Enter}second");
    await expect(textarea).toHaveValue("first\nsecond");
  },
};

export const Invalid: Story = {
  args: { invalid: true, invalidMessage: "Notes are too long" },
  play: async ({ canvasElement }) => {
    const textarea = within(canvasElement).getByLabelText("Notes");
    await expect(textarea).toHaveAttribute("aria-invalid", "true");
    await expect(textarea).toHaveAccessibleDescription("Shown on the run history Notes are too long");
  },
};

export const HiddenLabel: Story = {
  args: { hideLabel: true },
  play: async ({ canvasElement }) => {
    const input = within(canvasElement).getByLabelText("Notes");
    await expect(input).toBeVisible();
    const label = canvasElement.querySelector("label");
    await expect(label?.getBoundingClientRect().width).toBeLessThanOrEqual(1);
    await expect(input).toHaveAccessibleName("Notes");
  },
};

export const Disabled: Story = { args: { disabled: true } };

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
