import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { getListCoveredCatalogsMockHandler } from "@/api/generated/table-discovery-settings/table-discovery-settings.msw";
import { getGetTableMockHandler } from "@/api/generated/tables/tables.msw";
import { apiError } from "@/stories/apiError";
import { ConsolePage } from "@/stories/ConsolePage";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";
import { MAINTAINED_ORDERS } from "@/stories/storyData";

const ORDERS = "/catalogs/iceberg/namespaces/retail/tables/orders";

const meta = {
  title: "Pages/Table",
  component: ConsolePage,
  args: { route: ORDERS },
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof ConsolePage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Overview: Story = {
  play: async ({ canvasElement }) => {
    await expect(await within(canvasElement).findByRole("heading", { name: "orders" })).toBeVisible();
  },
};

export const Schema: Story = {
  args: { route: `${ORDERS}/schema` },
  play: async ({ canvasElement }) => {
    await expect(await within(canvasElement).findByText("customer_id")).toBeVisible();
  },
};

export const Snapshots: Story = { args: { route: `${ORDERS}/snapshots` } };

export const Commits: Story = { args: { route: `${ORDERS}/commits` } };

export const Maintenance: Story = { args: { route: `${ORDERS}/maintenance` } };

export const Settings: Story = { args: { route: `${ORDERS}/settings` } };

export const Properties: Story = { args: { route: `${ORDERS}/properties` } };

export const Paused: Story = {
  beforeEach({ msw }) {
    msw.use(getGetTableMockHandler({ ...MAINTAINED_ORDERS, status: "paused" }));
  },
};

export const CatalogNotCovered: Story = {
  beforeEach({ msw }) {
    msw.use(getListCoveredCatalogsMockHandler({ catalogs: [] }));
  },
  play: async ({ canvasElement }) => {
    await expect(
      await within(canvasElement).findByText("this catalog is not covered by maintenance"),
    ).toBeVisible();
  },
};

export const MaintenanceUnavailable: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("get", "/v1/tables/:tableUuid", "database down", 500));
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByRole("heading", { name: "orders" });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
