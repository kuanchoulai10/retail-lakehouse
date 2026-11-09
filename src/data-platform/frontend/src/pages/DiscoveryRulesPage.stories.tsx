import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { getListTableDiscoveryRulesMockHandler } from "@/api/generated/table-discovery-rules/table-discovery-rules.msw";
import { ConsolePage } from "@/stories/ConsolePage";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";

const meta = {
  title: "Pages/Discovery rules",
  component: ConsolePage,
  args: { route: "/discovery-rules" },
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof ConsolePage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    await expect(await within(canvasElement).findByText("iceberg.retail.*")).toBeVisible();
  },
};

export const NoRules: Story = {
  beforeEach({ msw }) {
    msw.use(getListTableDiscoveryRulesMockHandler([]));
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByText("iceberg.retail.*");
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
