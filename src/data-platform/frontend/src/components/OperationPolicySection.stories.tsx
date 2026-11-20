import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { PHONE } from "@/stories/phone";
import { ON_OFF, OptionSelectField } from "./forms/OptionSelectField";
import { WholeNumberField } from "./forms/WholeNumberField";
import { OperationPolicySection } from "./OperationPolicySection";

const meta = {
  title: "Components/Operation policy section",
  component: OperationPolicySection,
  args: {
    title: "Rewrite manifests",
    included: true,
    onIncludedChange: fn(),
    target: <WholeNumberField label="Small manifests at most" value="5" onChange={fn()} />,
    options: <OptionSelectField label="Use caching" value="" options={ON_OFF} onChange={fn()} />,
  },
} satisfies Meta<typeof OperationPolicySection>;

export default meta;
type Story = StoryObj<typeof meta>;

export const InThisPolicy: Story = {
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("group", { name: "Target" })).toBeVisible();
    await expect(within(canvas.getByRole("group", { name: "Options" })).getByText("Empty: the procedure's default.")).toBeVisible();
    await expect(canvas.getByRole("combobox", { name: "Use caching" })).toHaveTextContent("Procedure default");
    await userEvent.tab();
    await expect(canvas.getByRole("switch", { name: "In this policy" })).toHaveFocus();
    await userEvent.keyboard(" ");
    await expect(args.onIncludedChange).toHaveBeenCalledWith(false);
  },
};

export const NotInThisPolicy: Story = {
  args: { included: false },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("Not in this policy: this operation does not run on a schedule.")).toBeVisible();
    await expect(canvas.queryByRole("group", { name: "Target" })).toBeNull();
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
