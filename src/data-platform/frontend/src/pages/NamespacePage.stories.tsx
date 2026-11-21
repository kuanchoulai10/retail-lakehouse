import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { getListCatalogTablesMockHandler } from "@/api/generated/tables/tables.msw";
import { getListViewsMockHandler } from "@/api/generated/views/views.msw";
import { ConsolePage } from "@/stories/ConsolePage";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";

const meta = {
  title: "Pages/Namespace",
  component: ConsolePage,
  args: { route: "/catalogs/iceberg/namespaces/retail" },
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof ConsolePage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("link", { name: "orders" })).toBeVisible();
    await expect(canvas.getByRole("link", { name: "daily_revenue" })).toBeVisible();
  },
};

export const PolicyAttachedHere: Story = {
  play: async ({ canvasElement }) => {
    const panel = within(await within(canvasElement).findByRole("region", { name: "Policies" }));
    const [maintenance, discovery] = await panel.findAllByRole("listitem");
    await expect(maintenance).toHaveTextContent("Attached here");
    await expect(discovery).toHaveTextContent("From catalog iceberg");
    await expect(panel.queryByRole("button", { name: "Detach discovery policy" })).toBeNull();
    await userEvent.click(panel.getByRole("button", { name: "Detach maintenance policy" }));
    await expect(panel.queryByRole("alert")).toBeNull();
  },
};

export const Empty: Story = {
  beforeEach({ msw }) {
    msw.use(getListCatalogTablesMockHandler([]), getListViewsMockHandler([]));
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByRole("link", { name: "orders" });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
