import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import { expectFocusRing, expectNoHorizontalPageScroll } from "../../stories/assertions";
import { BarList } from "./BarList";

const PARTITIONS = [
  { name: "order_date=2026-11-17", value: 128 },
  { name: "order_date=2026-11-19", value: 512 },
  { name: "order_date=2026-11-18", value: 256 },
  { name: "order_date=2026-11-16", value: 0 },
];

const meta = {
  title: "Charts/BarList",
  component: BarList,
  args: { label: "Reducible files by partition", items: PARTITIONS },
  parameters: {
    docs: {
      description: {
        component:
          "No Serendie counterpart. A ranked list: each row's bar is its share of the largest " +
          "value, and the value is always written out. Rows are sorted largest first unless " +
          "`sorted` is false. With `onSelect` each row is a button. Expanded departs from " +
          "Serendie: rows are 36px high (44px below 768px and under a coarse pointer).",
      },
    },
  },
} satisfies Meta<typeof BarList>;

export default meta;

type Story = StoryObj<typeof meta>;

function bars(canvasElement: HTMLElement): HTMLElement[] {
  return [...canvasElement.querySelectorAll<HTMLElement>("[data-bar]")];
}

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const list = within(canvasElement).getByRole("list", { name: "Reducible files by partition" });
    const rows = within(list).getAllByRole("listitem");
    await expect(rows.map((row) => row.textContent)).toEqual([
      "order_date=2026-11-19512",
      "order_date=2026-11-18256",
      "order_date=2026-11-17128",
      "order_date=2026-11-160",
    ]);
    const [first, second, , last] = bars(canvasElement) as [HTMLElement, HTMLElement, HTMLElement, HTMLElement];
    await expect(first.style.width).toBe("100%");
    await expect(second.style.width).toBe("50%");
    await expect(last.style.width).toBe("0%");
    await expect(within(list).queryByRole("button")).toBeNull();
  },
};

export const Selectable: Story = {
  args: { onSelect: fn() },
  play: async ({ args, canvasElement }) => {
    const buttons = within(canvasElement).getAllByRole("button");
    await expect(buttons).toHaveLength(4);
    await userEvent.tab();
    await expectFocusRing(buttons[0] as HTMLElement);
    await userEvent.keyboard("{Enter}");
    await expect(args.onSelect).toHaveBeenCalledWith(expect.objectContaining({ name: "order_date=2026-11-19" }));
    await userEvent.tab();
    await expectFocusRing(buttons[1] as HTMLElement);
    await userEvent.keyboard(" ");
    await expect(args.onSelect).toHaveBeenLastCalledWith(expect.objectContaining({ name: "order_date=2026-11-18" }));
  },
};

export const KeepOrder: Story = {
  args: { sorted: false },
  play: async ({ canvasElement }) => {
    const rows = within(canvasElement).getAllByRole("listitem");
    await expect(rows[0]).toHaveTextContent("order_date=2026-11-17");
  },
};

export const Empty: Story = {
  args: { items: [], emptyText: "No partition has files to merge" },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("No partition has files to merge")).toBeVisible();
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  args: {
    items: [{ name: "a_partition_with_a_very_long_name=2026-11-19/hour=23/bucket=15", value: 40 }, ...PARTITIONS],
  },
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
