import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { expect, fn, userEvent, within } from "storybook/test";
import { expectFocusRing, expectNoHorizontalPageScroll } from "../../stories/assertions";
import { DiffList, type DiffListItem, type DiffListProps } from "./DiffList";

const SCHEMA_ITEMS: DiffListItem[] = [
  { id: "1", change: "unchanged", label: "order_id", after: "long" },
  {
    id: "2",
    change: "changed",
    label: "customer",
    tags: ["Renamed", "Type changed"],
    before: "int",
    after: "long",
    description: "Renamed from customer_id",
  },
  { id: "3", change: "unchanged", label: "shipping", after: "struct" },
  { id: "4", change: "changed", label: "shipping.postcode", depth: 1, tags: ["Type changed"], before: "int", after: "string" },
  { id: "5", change: "added", label: "coupon_code", after: "string", description: "Code the customer entered at checkout" },
  { id: "6", change: "removed", label: "legacy_flag", before: "boolean" },
];

const meta = {
  title: "Components/DiffList",
  component: DiffList,
  args: {
    caption: "Changes from v2 to v3",
    items: SCHEMA_ITEMS,
    onlyChanges: false,
    onOnlyChangesChange: fn(),
  },
  render: (args) => <Stateful {...args} />,
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
          "No Serendie counterpart. One list that compares two versions of something: each row " +
          "says its change in a sign (`+`, `−`, `~`) and a neutral badge, never a status colour, " +
          "and a removed row's label is struck through. A changed value reads `before → after`. " +
          "The switch hides unchanged rows. Expanded departs from Serendie: rows are 36px high " +
          "(44px below 768px and under a coarse pointer).",
      },
    },
  },
} satisfies Meta<typeof DiffList>;

export default meta;

type Story = StoryObj<typeof meta>;

function Stateful(props: DiffListProps) {
  const [onlyChanges, setOnlyChanges] = useState(props.onlyChanges);
  return (
    <DiffList
      {...props}
      onlyChanges={onlyChanges}
      onOnlyChangesChange={(next) => {
        setOnlyChanges(next);
        props.onOnlyChangesChange(next);
      }}
    />
  );
}

export const Default: Story = {
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    const toggle = canvas.getByRole("switch", { name: "Show changes only" });
    const list = canvas.getByRole("list", { name: "Changes from v2 to v3" });
    await expect(within(list).getAllByRole("listitem")).toHaveLength(6);
    await expect(canvas.getByText("4 changes")).toBeVisible();
    await userEvent.tab();
    await expectFocusRing(toggle);
    await userEvent.keyboard(" ");
    await expect(args.onOnlyChangesChange).toHaveBeenLastCalledWith(true);
    await expect(within(list).getAllByRole("listitem")).toHaveLength(4);
    await expect(canvas.getByText("4 changes")).toBeVisible();
    await userEvent.keyboard("{Enter}");
    await expect(args.onOnlyChangesChange).toHaveBeenLastCalledWith(false);
    await expect(within(list).getAllByRole("listitem")).toHaveLength(6);
  },
};

export const OnlyChanges: Story = {
  args: { onlyChanges: true },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("switch", { name: "Show changes only" })).toBeChecked();
    const rows = within(canvas.getByRole("list")).getAllByRole("listitem");
    await expect(rows).toHaveLength(4);
    await expect(rows[0]).toHaveTextContent("customer");
    await expect(rows[0]).toHaveTextContent("Renamed");
    await expect(rows[0]).toHaveTextContent("Type changed");
    await expect(rows[0]).toHaveTextContent("Renamed from customer_id");
    await expect(rows[2]).toHaveTextContent("Added");
    await expect(rows[3]).toHaveTextContent("Removed");
    await expect(canvas.queryByText("order_id")).toBeNull();
  },
};

export const NoChanges: Story = {
  args: {
    onlyChanges: true,
    items: SCHEMA_ITEMS.filter((item) => item.change === "unchanged"),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("No changes.")).toBeVisible();
    await expect(canvas.getByText("No changes")).toBeVisible();
    await expect(canvas.queryByRole("listitem")).toBeNull();
  },
};

export const Empty: Story = {
  args: { items: [] },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("Nothing to compare.")).toBeVisible();
    await expect(canvas.queryByRole("listitem")).toBeNull();
  },
};

export const TransformChange: Story = {
  args: {
    caption: "Changes from spec v0 to v1",
    items: [
      {
        id: "1",
        change: "changed",
        label: "order_day",
        tags: ["Transform changed"],
        before: "day(order_ts)",
        after: "hour(order_ts)",
      },
    ],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const row = canvas.getByRole("listitem");
    await expect(row).toHaveTextContent("day(order_ts)");
    await expect(row).toHaveTextContent("changed to");
    await expect(row).toHaveTextContent("hour(order_ts)");
    await expect(canvas.getByText("1 change")).toBeVisible();
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  args: {
    items: [
      {
        id: "1",
        change: "added",
        label: `payload.${"a_nested_field_with_a_very_long_name.".repeat(3)}x`.slice(0, 120),
        after: "string",
      },
      ...SCHEMA_ITEMS,
    ],
  },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getAllByRole("listitem")[0]?.textContent).toContain(
      "payload.a_nested_field_with_a_very_long_name.",
    );
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const Dense: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  args: {
    items: [
      { id: "1", change: "unchanged", label: "order_id", after: "long" },
      { id: "2", change: "added", label: "coupon_code", after: "string" },
      { id: "3", change: "removed", label: "legacy_flag", before: "boolean" },
    ],
  },
  play: async ({ canvasElement }) => {
    const rows = within(canvasElement).getAllByRole("listitem");
    await expect(rows.map((row) => row.getBoundingClientRect().height)).toEqual([36, 36, 36]);
  },
};
