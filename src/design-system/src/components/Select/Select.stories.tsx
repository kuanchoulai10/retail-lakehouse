import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, waitFor, within } from "storybook/test";
import {
  expectFocusRing,
  expectNoHorizontalPageScroll,
  portalQueries,
} from "../../stories/assertions";
import { Select } from "./Select";

const meta = {
  title: "Components/Select",
  component: Select,
  args: {
    label: "Maintenance action",
    placeholder: "Choose an action",
    items: [
      { value: "compaction", label: "Compaction" },
      { value: "expire-snapshots", label: "Snapshot expiry" },
      { value: "remove-orphans", label: "Remove orphan files" },
    ],
    onValueChange: fn(),
  },
  decorators: [
    (Story) => (
      <div className="h-72 max-w-sm p-4">
        <Story />
      </div>
    ),
  ],
  parameters: {
    docs: {
      description: {
        component:
          "Expanded departs from Serendie: the trigger and options are 36px high (Serendie " +
          "48px) and stay 44px below 768px and under a coarse pointer.",
      },
    },
  },
} satisfies Meta<typeof Select>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    const portal = portalQueries(canvasElement);
    const trigger = canvas.getByRole("combobox", { name: "Maintenance action" });
    await userEvent.tab();
    await expectFocusRing(trigger);
    await userEvent.keyboard("{Enter}");
    const first = await portal.findByRole("option", { name: "Compaction" });
    await waitFor(() => expect(first).toHaveFocus());
    await userEvent.keyboard("{ArrowDown}");
    await waitFor(() => expect(portal.getByRole("option", { name: "Snapshot expiry" })).toHaveFocus());
    await userEvent.keyboard("{Enter}");
    await expect(args.onValueChange).toHaveBeenLastCalledWith("expire-snapshots");
    await waitFor(() => expect(portal.queryByRole("listbox")).toBeNull());
    await waitFor(() => expect(trigger).toHaveFocus());
    await expect(trigger).toHaveTextContent("Snapshot expiry");
    await userEvent.keyboard("{Enter}");
    await portal.findByRole("listbox");
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(portal.queryByRole("listbox")).toBeNull());
    await waitFor(() => expect(trigger).toHaveFocus());
  },
};

export const Invalid: Story = {
  args: { invalid: true, invalidMessage: "Pick an action", description: "Runs on the table" },
  play: async ({ canvasElement }) => {
    const trigger = within(canvasElement).getByRole("combobox", { name: "Maintenance action" });
    await expect(trigger).toHaveAttribute("aria-invalid", "true");
    await expect(trigger).toHaveAccessibleDescription("Runs on the table Pick an action");
  },
};

export const Selected: Story = {
  args: { value: "compaction" },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("combobox")).toHaveTextContent("Compaction");
  },
};

export const Disabled: Story = {
  args: { disabled: true },
  play: async ({ canvasElement }) => {
    const trigger = within(canvasElement).getByRole("combobox");
    await expect(trigger).toBeDisabled();
    await userEvent.tab();
    await expect(trigger).not.toHaveFocus();
  },
};

export const Touch: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  play: async ({ canvasElement }) => {
    const trigger = within(canvasElement).getByRole("combobox");
    await expect(trigger.getBoundingClientRect().height).toBe(44);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const Desktop: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  play: async ({ canvasElement }) => {
    const trigger = within(canvasElement).getByRole("combobox");
    await expect(trigger.getBoundingClientRect().height).toBe(36);
    await userEvent.click(trigger);
    const option = await portalQueries(canvasElement).findByRole("option", { name: "Compaction" });
    await expect(option.getBoundingClientRect().height).toBe(36);
    await userEvent.keyboard("{Escape}");
  },
};
