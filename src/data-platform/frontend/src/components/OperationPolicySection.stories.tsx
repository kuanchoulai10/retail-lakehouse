import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { PHONE } from "@/stories/phone";
import { WholeNumberField } from "./forms/WholeNumberField";
import { OperationPolicySection } from "./OperationPolicySection";

function field(label: string, value: string, unit?: "seconds" | "bytes") {
  return { label, value, unit, onChange: fn() };
}

const meta = {
  title: "Components/Operation policy section",
  component: OperationPolicySection,
  args: {
    title: "Rewrite manifests",
    enabled: true,
    onEnabledChange: fn(),
    cooldown: field("Cooldown (seconds)", "21600", "seconds"),
    conditions: [
      {
        label: "Small manifests",
        fields: [field("Small manifests at least", "5"), field("Smaller than (bytes)", "", "bytes")],
      },
      { label: "Manifest count", fields: [field("Manifests at least", "")] },
    ],
  },
} satisfies Meta<typeof OperationPolicySection>;

export default meta;
type Story = StoryObj<typeof meta>;

// Two conditions to show the "or" between them; the real operations have one each today.
export const Conditions: Story = {
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    const trigger = canvas.getByRole("group", { name: "Trigger" });
    await expect(within(trigger).getByText("or", { exact: true })).toBeVisible();
    await expect(within(trigger).getByText("6 h")).toBeVisible();
    await userEvent.tab();
    await expect(canvas.getByRole("switch", { name: "Enabled" })).toHaveFocus();
    await userEvent.keyboard(" ");
    await expect(args.onEnabledChange).toHaveBeenCalledWith(false);
  },
};

export const WithScopeAndExecution: Story = {
  args: {
    title: "Rewrite data files",
    scope: { value: "partition", onChange: fn() },
    conditions: [{ label: "Reducible files", fields: [field("Reducible files at least", "5")] }],
    children: <WholeNumberField label="Min input files" value="2" onChange={fn()} />,
  },
};

export const NoConditions: Story = {
  args: { title: "Remove orphan files", conditions: [] },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("No conditions: due once the cooldown has passed.")).toBeVisible();
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
