import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
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

export const Default: Story = {
  play: async ({ canvasElement }) => {
    await expect(await within(canvasElement).findByText("iceberg.inventory.stock_levels")).toBeVisible();
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
