import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { getListNamespacesMockHandler } from "@/api/generated/namespaces/namespaces.msw";
import { apiError } from "@/stories/apiError";
import { ConsolePage } from "@/stories/ConsolePage";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";

const meta = {
  title: "Pages/Catalog",
  component: ConsolePage,
  args: { route: "/catalogs/iceberg" },
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof ConsolePage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("link", { name: "retail" })).toBeVisible();
    await expect(canvas.getByRole("link", { name: "inventory" })).toBeVisible();
  },
};

export const NoNamespaces: Story = {
  beforeEach({ msw }) {
    msw.use(getListNamespacesMockHandler([]));
  },
};

export const NotFound: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("get", "/v1/catalogs/:catalog", "catalog iceberg not found", 404));
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByRole("link", { name: "retail" });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
