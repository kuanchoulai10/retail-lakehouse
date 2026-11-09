import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
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
