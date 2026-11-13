import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { expect, fn, userEvent, waitFor, within } from "storybook/test";
import {
  expectFocusRing,
  expectNoHorizontalPageScroll,
  portalQueries,
} from "../../stories/assertions";
import { MultiSelect, type MultiSelectProps } from "./MultiSelect";

const ITEMS = [
  { value: "managed", label: "Managed" },
  { value: "unmanaged", label: "Unmanaged" },
  { value: "dropped", label: "Dropped" },
];

const meta = {
  title: "Components/MultiSelect",
  component: MultiSelect,
  args: {
    label: "Status",
    items: ITEMS,
    value: ["managed", "unmanaged"],
    onValueChange: fn(),
  },
  render: function Render({ value: initial, onValueChange, ...args }: MultiSelectProps) {
    const [value, setValue] = useState(initial);
    return (
      <MultiSelect
        {...args}
        value={value}
        onValueChange={(next) => {
          setValue(next);
          onValueChange(next);
        }}
      />
    );
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
          "No Serendie counterpart (Serendie's Select is single choice). A trigger that lists the " +
          "chosen labels, opening a menu of check items that stays open while you toggle. " +
          "Expanded departs from Serendie: the trigger and items are 36px high and stay 44px " +
          "below 768px and under a coarse pointer.",
      },
    },
  },
} satisfies Meta<typeof MultiSelect>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    const portal = portalQueries(canvasElement);
    const trigger = canvas.getByRole("button", { name: /Status/ });
    await expect(trigger).toHaveTextContent("Managed, Unmanaged");
    await userEvent.tab();
    await expectFocusRing(trigger);
    await userEvent.keyboard("{Enter}");
    const managed = await portal.findByRole("menuitemcheckbox", { name: "Managed" });
    await waitFor(() => expect(managed).toHaveFocus());
    await expect(managed).toBeChecked();
    await expect(portal.getByRole("menuitemcheckbox", { name: "Dropped" })).not.toBeChecked();
    await userEvent.keyboard("{ArrowDown}{ArrowDown}");
    const dropped = portal.getByRole("menuitemcheckbox", { name: "Dropped" });
    await expect(dropped).toHaveFocus();
    await userEvent.keyboard(" ");
    await expect(args.onValueChange).toHaveBeenLastCalledWith(["managed", "unmanaged", "dropped"]);
    await expect(dropped).toBeChecked();
    await expect(portal.getByRole("menu")).toBeVisible();
    await userEvent.keyboard("{ArrowUp}{Enter}");
    await expect(args.onValueChange).toHaveBeenLastCalledWith(["managed", "dropped"]);
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(portal.queryByRole("menu")).toBeNull());
    await waitFor(() => expect(trigger).toHaveFocus());
    await expect(trigger).toHaveTextContent("Managed, Dropped");
  },
};

export const NothingSelected: Story = {
  args: { value: [] },
  play: async ({ canvasElement, args }) => {
    const trigger = within(canvasElement).getByRole("button", { name: /Status/ });
    await expect(trigger).toHaveTextContent("None selected");
    await userEvent.tab();
    await userEvent.keyboard("{Enter}");
    const managed = await portalQueries(canvasElement).findByRole("menuitemcheckbox", { name: "Managed" });
    await waitFor(() => expect(managed).toHaveFocus());
    await expect(managed).not.toBeChecked();
    await userEvent.keyboard(" ");
    await expect(args.onValueChange).toHaveBeenLastCalledWith(["managed"]);
    await userEvent.keyboard("{Escape}");
  },
};

export const AllSelected: Story = {
  args: { value: ["managed", "unmanaged", "dropped"] },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("button", { name: /Status/ })).toHaveTextContent(
      "Managed, Unmanaged, Dropped",
    );
  },
};

export const Disabled: Story = {
  args: { disabled: true },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("button", { name: /Status/ })).toBeDisabled();
  },
};

export const Touch: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  play: async ({ canvasElement }) => {
    const trigger = within(canvasElement).getByRole("button", { name: /Status/ });
    await expect(trigger.getBoundingClientRect().height).toBe(44);
    await userEvent.click(trigger);
    const item = await portalQueries(canvasElement).findByRole("menuitemcheckbox", { name: "Managed" });
    await expect(item.getBoundingClientRect().height).toBe(44);
    await userEvent.keyboard("{Escape}");
  },
};

export const Desktop: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  play: async ({ canvasElement }) => {
    const trigger = within(canvasElement).getByRole("button", { name: /Status/ });
    await expect(trigger.getBoundingClientRect().height).toBe(36);
    await userEvent.click(trigger);
    const item = await portalQueries(canvasElement).findByRole("menuitemcheckbox", { name: "Managed" });
    await expect(item.getBoundingClientRect().height).toBe(36);
    await userEvent.keyboard("{Escape}");
  },
};

export const PhoneLongSummary: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  args: {
    items: [
      { value: "a", label: "A very long category label that cannot fit" },
      { value: "b", label: "Another very long category label" },
    ],
    value: ["a", "b"],
  },
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
