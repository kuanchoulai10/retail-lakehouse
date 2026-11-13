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
    await expect(statusFilter(canvasElement)).toHaveTextContent("Managed, Unmanaged");
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
    await expect(statusFilter(canvasElement)).toHaveTextContent("Unmanaged, Dropped");
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
  args: { route: "/?status=managed,unmanaged,dropped" },
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByText("iceberg.retail.legacy_orders");
    await expect(statusFilter(canvasElement)).toHaveTextContent("Managed, Unmanaged, Dropped");
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
