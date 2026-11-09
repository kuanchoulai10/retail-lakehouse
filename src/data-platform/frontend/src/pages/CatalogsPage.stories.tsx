import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { getListCatalogsMockHandler } from "@/api/generated/catalogs/catalogs.msw";
import { apiError } from "@/stories/apiError";
import { apiPending } from "@/stories/apiPending";
import { ConsolePage } from "@/stories/ConsolePage";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";

const meta = {
  title: "Pages/Catalogs",
  component: ConsolePage,
  args: { route: "/catalogs" },
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof ConsolePage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("link", { name: "iceberg" })).toBeVisible();
    await expect(canvas.getByRole("link", { name: "analytics" })).toBeVisible();
  },
};

export const Empty: Story = {
  beforeEach({ msw }) {
    msw.use(getListCatalogsMockHandler([]));
  },
  play: async ({ canvasElement }) => {
    await expect(await within(canvasElement).findByText("No catalogs.")).toBeVisible();
  },
};

export const PolarisUnreachable: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("get", "/v1/catalogs", "could not get a Polaris token, Polaris is unreachable"));
  },
  play: async ({ canvasElement }) => {
    await expect(await within(canvasElement).findByText(/Could not load catalogs/)).toBeVisible();
  },
};

export const Loading: Story = {
  beforeEach({ msw }) {
    msw.use(apiPending("/v1/catalogs"));
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findAllByRole("link", { name: "iceberg" });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
