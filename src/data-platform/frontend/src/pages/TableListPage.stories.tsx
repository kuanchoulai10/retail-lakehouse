import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, waitFor, within } from "storybook/test";
import { getListTablesMockHandler } from "@/api/generated/tables/tables.msw";
import { ConsolePage } from "@/stories/ConsolePage";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";

const meta = {
  title: "Pages/Maintained tables",
  component: ConsolePage,
  args: { route: "/" },
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof ConsolePage>;

export default meta;
type Story = StoryObj<typeof meta>;

function statusFilter(canvasElement: HTMLElement): HTMLElement {
  const filter = canvasElement.ownerDocument.getElementById("status-filter");
  if (!filter) throw new Error("status filter not found");
  return filter;
}

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("iceberg.inventory.stock_levels")).toBeVisible();
    await expect(canvas.getByText("iceberg.retail.customers")).toBeVisible();
    await expect(canvas.queryByText("iceberg.retail.legacy_orders")).toBeNull();
    await expect(statusFilter(canvasElement)).toHaveTextContent("Managed, Unmanaged, Undecided");
  },
};

// A table a policy was attached to before discovery saw it shows by default, in the grey group badge.
export const Undecided: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const row = (await canvas.findByText("iceberg.sales.returns")).closest("tr") as HTMLElement;
    await expect(within(row).getByText("Undecided")).toBeVisible();
    await userEvent.click(statusFilter(canvasElement));
    const portal = within(canvasElement.ownerDocument.body);
    await userEvent.click(await portal.findByRole("menuitemcheckbox", { name: "Undecided" }));
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(canvas.queryByText("iceberg.sales.returns")).toBeNull());
    await expect(canvas.getByText("iceberg.retail.customers")).toBeVisible();
  },
};

export const MultiSelect: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const portal = within(canvasElement.ownerDocument.body);
    await canvas.findByText("iceberg.inventory.stock_levels");
    await userEvent.click(statusFilter(canvasElement));
    await userEvent.click(await portal.findByRole("menuitemcheckbox", { name: "Dropped" }));
    await userEvent.click(await portal.findByRole("menuitemcheckbox", { name: "Managed" }));
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(portal.queryByRole("menu")).toBeNull());
    await expect(canvas.getByText("iceberg.retail.legacy_orders")).toBeVisible();
    await expect(canvas.getByText("iceberg.retail.customers")).toBeVisible();
    await expect(canvas.queryByText("iceberg.retail.orders")).toBeNull();
    await expect(statusFilter(canvasElement)).toHaveTextContent("Unmanaged, Undecided, Dropped");
  },
};

export const FromUrl: Story = {
  args: { route: "/?status=dropped" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("iceberg.retail.legacy_orders")).toBeVisible();
    await expect(canvas.queryByText("iceberg.retail.orders")).toBeNull();
    await expect(statusFilter(canvasElement)).toHaveTextContent("Dropped");
  },
};

export const NothingSelected: Story = {
  args: { route: "/?status=" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("No status selected.")).toBeVisible();
    await expect(canvas.queryByText("iceberg.retail.orders")).toBeNull();
    await expect(statusFilter(canvasElement)).toHaveTextContent("None selected");
  },
};

export const TimeColumns: Story = {
  args: { route: "/?status=managed,unmanaged,dropped" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const customers = (await canvas.findByText("iceberg.retail.customers")).closest("tr") as HTMLElement;
    await expect(canvas.getByRole("columnheader", { name: /Last commit/ })).toBeVisible();
    await expect(canvas.getByRole("columnheader", { name: /Last discovered/ })).toBeVisible();
    await expect(canvas.queryByRole("columnheader", { name: /Updated/ })).toBeNull();
    await expect(within(customers).getByText("—")).toBeVisible();
    const dropped = canvas.getByText("iceberg.retail.legacy_orders").closest("tr") as HTMLElement;
    const times = [...dropped.querySelectorAll("time")].map((time) => time.getAttribute("datetime"));
    await expect(times).toEqual(["2026-11-05T16:20:00Z", "2026-11-06T09:00:00Z"]);
  },
};

export const Empty: Story = {
  beforeEach({ msw }) {
    msw.use(getListTablesMockHandler([]));
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByText("iceberg.inventory.stock_levels");
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const PhoneAllStatuses: Story = {
  globals: PHONE,
  args: { route: "/?status=managed,unmanaged,undecided,dropped" },
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByText("iceberg.retail.legacy_orders");
    await expect(statusFilter(canvasElement)).toHaveTextContent("Managed, Unmanaged, Undecided, Dropped");
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
