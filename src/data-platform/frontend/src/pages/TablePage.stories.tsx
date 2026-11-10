import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { getListCoveredCatalogsMockHandler } from "@/api/generated/table-discovery-settings/table-discovery-settings.msw";
import { getGetTableMockHandler } from "@/api/generated/tables/tables.msw";
import { getListTableReconciliationsMockHandler } from "@/api/generated/table-reconciliations/table-reconciliations.msw";
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

export const Commits: Story = { args: { route: `${ORDERS}/commits` } };

export const CommitsBySpark: Story = {
  args: { route: `${ORDERS}/commits?writer=spark` },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("Delete: 42 rows removed")).toBeVisible();
    await expect(canvas.queryByText("Append: 1,200 rows added in 4 files")).toBeNull();
    await expect(canvas.getByRole("combobox", { name: "Writer" })).toHaveTextContent("Spark");
  },
};

export const CommitsPhone: Story = {
  args: { route: `${ORDERS}/commits` },
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByText("Delete: 42 rows removed");
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const Maintenance: Story = { args: { route: `${ORDERS}/maintenance` } };

export const Settings: Story = { args: { route: `${ORDERS}/settings` } };

export const Reconciliations: Story = {
  args: { route: `${ORDERS}/reconciliations` },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("button", { name: /^Started Rewrite data files/ })).toBeVisible();
    await expect(canvas.getByRole("button", { name: /^4 reconciliations found nothing to do/ })).toBeVisible();
    await expect(canvas.getByRole("button", { name: /^Would start Rewrite data files/ })).toHaveTextContent("Dry run");
    await expect(canvas.getByRole("button", { name: /^Skipped: table paused/ })).toBeVisible();
    await expect(canvas.getByRole("link", { name: "Open maintenance run run-1" })).toHaveTextContent(/^Run run-1$/);
    const day = canvas.getByRole("region", { name: /^Reconciliations on / });
    for (const part of Array.from(day.querySelectorAll<HTMLElement>("ul, li, button"))) {
      const style = getComputedStyle(part);
      await expect(
        [style.borderTopWidth, style.borderRightWidth, style.borderBottomWidth, style.borderLeftWidth],
      ).toEqual(["0px", "0px", "0px", "0px"]);
    }
  },
};

export const ReconciliationDrawer: Story = {
  args: { route: `${ORDERS}/reconciliations` },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("button", { name: /^Started Rewrite data files/ }));
    const drawer = within(await within(canvasElement.ownerDocument.body).findByRole("dialog"));
    await expect(drawer.getByRole("heading", { level: 2, name: "Started Rewrite data files" })).toBeVisible();
    await expect(drawer.getByText(/Catalog commit × 3/)).toBeVisible();
    await expect(drawer.getByRole("link", { name: "Open maintenance run run-1" })).toHaveAttribute(
      "href",
      `${ORDERS}/maintenance?run=run-1`,
    );
    const measurements = drawer.getAllByRole("button", { name: "All measurements" })[0]!;
    await userEvent.click(measurements);
    await expect(measurements).toHaveAttribute("aria-expanded", "true");
    await expect(drawer.getByRole("list", { name: "All measurements of Rewrite data files" })).toBeVisible();
  },
};

export const ReconciliationsEmpty: Story = {
  args: { route: `${ORDERS}/reconciliations` },
  beforeEach({ msw }) {
    msw.use(getListTableReconciliationsMockHandler([]));
  },
  play: async ({ canvasElement }) => {
    await expect(await within(canvasElement).findByText("No reconciliations yet.")).toBeVisible();
  },
};

export const ReconciliationsError: Story = {
  args: { route: `${ORDERS}/reconciliations` },
  beforeEach({ msw }) {
    msw.use(apiError("get", "/v1/tables/:tableUuid/reconciliations", "database down", 500));
  },
  play: async ({ canvasElement }) => {
    await expect(
      await within(canvasElement).findByText("Could not load reconciliations: database down"),
    ).toBeVisible();
  },
};

export const ReconciliationsPhone: Story = {
  args: { route: `${ORDERS}/reconciliations` },
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByRole("button", { name: /^Started Rewrite data files/ });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const Properties: Story = { args: { route: `${ORDERS}/properties` } };

export const Paused: Story = {
  beforeEach({ msw }) {
    msw.use(getGetTableMockHandler({ ...MAINTAINED_ORDERS, status: "paused" }));
  },
};

export const DryRunHeader: Story = {
  beforeEach({ msw }) {
    msw.use(getGetTableMockHandler({ ...MAINTAINED_ORDERS, settings: { dry_run: true } }));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("Dry run")).toBeVisible();
    await expect(canvas.getByRole("button", { name: "Reconcile now" })).toBeEnabled();
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
