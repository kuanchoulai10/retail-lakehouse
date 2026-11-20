import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, screen, userEvent, waitFor, within } from "storybook/test";
import { getListCoveredCatalogsMockHandler } from "@/api/generated/discovery-rules/discovery-rules.msw";
import { getGetTableApplicableMaintenancePolicyMockHandler } from "@/api/generated/maintenance-policies/maintenance-policies.msw";
import { getListTableMaintenanceRunsMockHandler } from "@/api/generated/table-maintenance-runs/table-maintenance-runs.msw";
import {
  getGetCatalogTablePartitionSpecComparisonMockHandler,
  getGetCatalogTableSchemaComparisonMockHandler,
  getGetTableCurrentMetricsMockHandler,
  getGetTableMockHandler,
  getListCatalogTablePartitionSpecVersionsMockHandler,
  getListCatalogTableSchemaVersionsMockHandler,
} from "@/api/generated/tables/tables.msw";
import { getListTableReconciliationsMockHandler } from "@/api/generated/table-reconciliations/table-reconciliations.msw";
import { temporalWorkflowsUrl } from "@/lib/temporalWorkflowsUrl";
import { apiError } from "@/stories/apiError";
import { ConsolePage } from "@/stories/ConsolePage";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";
import {
  ESCALATED_RUN,
  ESCALATED_RUN_ID,
  inFlightRun,
  IN_FLIGHT_RUN_ID,
  MAINTAINED_ORDERS,
  ORDERS_HOURLY_SPEC_COMPARISON,
  ORDERS_HOURLY_SPEC_VERSIONS,
  ordersManySchemaVersions,
  ordersSchemaComparison,
  POLICIES,
  QUEUE_TIMEOUT_RUN,
  QUEUE_TIMEOUT_RUN_ID,
  queuedRun,
  SCHEDULED_RUN_ID,
} from "@/stories/storyData";

const ORDERS = "/catalogs/iceberg/namespaces/retail/tables/orders";
const METRIC_CARDS = ["Data files", "Data size", "Total rows", "Reducible files", "Snapshots", "Manifests"];
const METRIC_SECTIONS = ["Files", "Size", "Rows", "Reducible files", "Manifests", "Snapshots"];

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
    const canvas = within(canvasElement);
    const header = within((await canvas.findByRole("heading", { name: "orders" })).closest("header") as HTMLElement);
    await expect(header.queryByText("Managed")).toBeNull();
    await expect(header.queryByText(/Policy:|Rule:/)).toBeNull();
    const table = within(await canvas.findByRole("region", { name: "Table" }));
    await expect(await table.findByRole("link", { name: "Priority 10" })).toHaveAttribute("href", "/discovery-rules");
    await expect(await table.findByRole("combobox", { name: "Priority" })).toHaveTextContent("P3 · default");
    for (const label of METRIC_CARDS) {
      await expect(await canvas.findByRole("group", { name: label })).toBeVisible();
    }
    await expect(await within(canvas.getByRole("group", { name: "Data files" })).findByText("1,174")).toBeVisible();
    await expect(canvas.getByText(/^Measured /)).toBeVisible();
    await canvas.findByRole("region", { name: "Maintenance policy" });
    await expect(canvas.getAllByRole("region").map((region) => region.querySelector("h2")?.textContent)).toEqual([
      ...METRIC_SECTIONS,
      "Table",
      "Maintenance policy",
    ]);
  },
};

export const OverviewTrendsUnavailable: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("get", "/v1/tables/:tableUuid/metrics", "Prometheus did not answer", 502));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => expect(canvas.getAllByText("Trends unavailable: Prometheus did not answer")).toHaveLength(7));
    await expect(await within(await canvas.findByRole("group", { name: "Data files" })).findByText("1,174")).toBeVisible();
  },
};

export const OverviewNotReconciledYet: Story = {
  beforeEach({ msw }) {
    msw.use(getGetTableCurrentMetricsMockHandler({ observed_at: null, metrics: null }));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("Metrics appear after the table's next reconciliation.")).toBeVisible();
    for (const label of METRIC_CARDS) {
      await expect(canvas.getByRole("group", { name: label })).toHaveTextContent("—");
    }
  },
};

export const OverviewCurrentUnavailable: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("get", "/v1/tables/:tableUuid/metrics/current", "database down", 502));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("alert")).toHaveTextContent("Could not load the current metrics: database down");
    for (const label of METRIC_CARDS) {
      await expect(canvas.getByRole("group", { name: label })).toHaveTextContent("—");
    }
    await waitFor(() =>
      expect(canvasElement.querySelectorAll('svg.recharts-surface[tabindex="0"]')).toHaveLength(7),
    );
  },
};

export const OverviewPhone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await within(await canvas.findByRole("group", { name: "Data files" })).findByText("1,174")).toBeVisible();
    await waitFor(() =>
      expect(canvasElement.querySelectorAll('svg.recharts-surface[tabindex="0"]')).toHaveLength(7),
    );
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

// Properties are edited in the Properties tab, so the header's menu holds Rename and Delete only.
export const Actions: Story = {
  play: async ({ canvasElement }) => {
    await userEvent.click(await within(canvasElement).findByRole("button", { name: "Actions" }));
    const items = await screen.findAllByRole("menuitem");
    await expect(items.map((item) => item.textContent)).toEqual(["Rename", "Delete"]);
    // Closed again, so the page axe checks is not hidden behind the open menu.
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("menu")).toBeNull());
  },
};

// The row button of a version in a panel's version list (a version's name is the text inside its button).
async function versionButton(panel: ReturnType<typeof within>, version: string): Promise<HTMLElement> {
  const list = within(await panel.findByRole("list", { name: /versions$/ }));
  return list.getByText(version).closest("button") as HTMLElement;
}

export const Schema: Story = {
  args: { route: `${ORDERS}/schema` },
  play: async ({ canvasElement }) => {
    const schema = within(await within(canvasElement).findByRole("region", { name: "Schema" }));
    const newest = await versionButton(schema, "v1");
    await expect(newest).toHaveTextContent("Current");
    await expect(newest).toHaveTextContent("+5 added · 1 doc changed");
    await expect(await schema.findByText("customer_id")).toBeVisible();
    await expect(await schema.findByText("shipping.zip")).toBeVisible();
    const spec = within(await within(canvasElement).findByRole("region", { name: "Partition spec" }));
    await expect(await versionButton(spec, "v0")).toHaveTextContent("Default");
  },
};

export const SchemaCompareTwoVersions: Story = {
  args: { route: `${ORDERS}/schema?schema=0&base=1` },
  play: async ({ canvasElement }) => {
    const schema = within(await within(canvasElement).findByRole("region", { name: "Schema" }));
    const list = within(await schema.findByRole("list", { name: "Changes in schema v0" }));
    await expect(await list.findByText("coupon_code")).toBeVisible();
    await expect(list.getAllByText("Removed")).toHaveLength(5);
    await expect(schema.getByRole("combobox", { name: "Compare with" })).toHaveTextContent("v1");
  },
};

export const SchemaOnlyChanges: Story = {
  args: { route: `${ORDERS}/schema` },
  play: async ({ canvasElement }) => {
    const schema = within(await within(canvasElement).findByRole("region", { name: "Schema" }));
    await expect(await schema.findByText("customer_id")).toBeVisible();
    await userEvent.click(schema.getByRole("switch", { name: "Show changes only" }));
    await waitFor(() => expect(schema.queryByText("customer_id")).toBeNull());
    await expect(schema.getByText("coupon_code")).toBeVisible();
    await expect(schema.getByText("order_id")).toBeVisible();
  },
};

export const SchemaManyVersions: Story = {
  args: { route: `${ORDERS}/schema` },
  beforeEach({ msw }) {
    msw.use(
      getListCatalogTableSchemaVersionsMockHandler(ordersManySchemaVersions(12)),
      getGetCatalogTableSchemaComparisonMockHandler(({ params }) => ({
        ...ordersSchemaComparison(1, 0),
        schema_id: Number(params.schemaId),
        base_schema_id: Number(params.schemaId) - 1,
      })),
    );
  },
  play: async ({ canvasElement }) => {
    const schema = within(await within(canvasElement).findByRole("region", { name: "Schema" }));
    const more = await schema.findByRole("button", { name: "Show 2 earlier versions" });
    const list = within(schema.getByRole("list", { name: "Schema versions" }));
    await expect(list.queryByText("v0")).toBeNull();
    await userEvent.click(more);
    await expect(await list.findByText("v0")).toBeVisible();
  },
};

export const SchemaPartitionTransformChange: Story = {
  args: { route: `${ORDERS}/schema` },
  beforeEach({ msw }) {
    msw.use(
      getListCatalogTablePartitionSpecVersionsMockHandler(ORDERS_HOURLY_SPEC_VERSIONS),
      getGetCatalogTablePartitionSpecComparisonMockHandler(ORDERS_HOURLY_SPEC_COMPARISON),
    );
  },
  play: async ({ canvasElement }) => {
    const spec = within(await within(canvasElement).findByRole("region", { name: "Partition spec" }));
    await expect(await versionButton(spec, "v1")).toHaveTextContent("Default");
    const row = (await spec.findByText("ordered_at_hour")).closest("li") as HTMLElement;
    await expect(row).toHaveTextContent("Transform changed");
    await expect(row).toHaveTextContent("day(ordered_at)");
    await expect(row).toHaveTextContent("hour(ordered_at)");
  },
};

export const SchemaVersionsError: Story = {
  args: { route: `${ORDERS}/schema` },
  beforeEach({ msw }) {
    msw.use(
      apiError("get", "/v1/catalogs/:catalog/namespaces/:namespace/tables/:table/schema-versions", "Polaris is unreachable"),
    );
  },
  play: async ({ canvasElement }) => {
    await expect(
      await within(canvasElement).findByText("Could not load schema versions: Polaris is unreachable"),
    ).toBeVisible();
  },
};

export const SchemaPhone: Story = {
  args: { route: `${ORDERS}/schema` },
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByText("shipping.zip");
    await within(canvasElement).findByRole("list", { name: "Changes in partition spec v0" });
    await expectNoHorizontalPageScroll(canvasElement);
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

export const Maintenance: Story = {
  args: { route: `${ORDERS}/maintenance` },
  play: async ({ canvasElement }) => {
    const link = await within(canvasElement).findByRole("link", { name: "Running workflows in Temporal" });
    await expect(link).toHaveAttribute("href", temporalWorkflowsUrl(MAINTAINED_ORDERS.uuid));
  },
};

async function openEscalatedRun(canvasElement: HTMLElement) {
  const canvas = within(canvasElement);
  await userEvent.click(await canvas.findByRole("button", { name: `Expand run ${ESCALATED_RUN_ID}` }));
  return within(canvas.getByRole("table", { name: "Attempts of rewrite_data_files" }));
}

export const MaintenanceAttemptsEscalated: Story = {
  args: { route: `${ORDERS}/maintenance` },
  beforeEach({ msw }) {
    msw.use(getListTableMaintenanceRunsMockHandler([ESCALATED_RUN]));
  },
  play: async ({ canvasElement }) => {
    const attempts = await openEscalatedRun(canvasElement);
    await expect(attempts.getByText("Out of memory")).toBeVisible();
    await expect(attempts.getByText("Did not finish")).toBeVisible();
    await expect(attempts.getByText("Retrying at size M")).toBeVisible();
    await expect(attempts.getByText("Done")).toBeVisible();
  },
};

export const MaintenanceAttemptsEscalatedPhone: Story = {
  args: { route: `${ORDERS}/maintenance` },
  globals: PHONE,
  beforeEach({ msw }) {
    msw.use(getListTableMaintenanceRunsMockHandler([ESCALATED_RUN]));
  },
  play: async ({ canvasElement }) => {
    await openEscalatedRun(canvasElement);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

async function openRun(canvasElement: HTMLElement, runId: string) {
  const canvas = within(canvasElement);
  await userEvent.click(await canvas.findByRole("button", { name: `Expand run ${runId}` }));
  return within(canvas.getByRole("table", { name: "Attempts of rewrite_data_files" }));
}

export const MaintenanceAttemptRunning: Story = {
  args: { route: `${ORDERS}/maintenance` },
  beforeEach({ msw }) {
    msw.use(getListTableMaintenanceRunsMockHandler([inFlightRun()]));
  },
  play: async ({ canvasElement }) => {
    const attempts = await openRun(canvasElement, IN_FLIGHT_RUN_ID);
    await expect(attempts.getByText(/\(running\)$/)).toBeVisible();
    await expect(attempts.getByText("Out of memory")).toBeVisible();
  },
};

export const MaintenanceAttemptQueued: Story = {
  args: { route: `${ORDERS}/maintenance` },
  beforeEach({ msw }) {
    msw.use(getListTableMaintenanceRunsMockHandler([queuedRun()]));
  },
  play: async ({ canvasElement }) => {
    const attempts = await openRun(canvasElement, IN_FLIGHT_RUN_ID);
    await expect(attempts.getByText(/\(waiting\)$/)).toBeVisible();
  },
};

export const MaintenanceQueueTimeout: Story = {
  args: { route: `${ORDERS}/maintenance` },
  beforeEach({ msw }) {
    msw.use(getListTableMaintenanceRunsMockHandler([QUEUE_TIMEOUT_RUN]));
  },
  play: async ({ canvasElement }) => {
    const attempts = await openRun(canvasElement, QUEUE_TIMEOUT_RUN_ID);
    await expect(attempts.getByText("Waited too long in the queue")).toBeVisible();
    await expect(attempts.getByText("24h 0m")).toBeVisible();
  },
};

export const MaintenanceQueuedPhone: Story = {
  args: { route: `${ORDERS}/maintenance` },
  globals: PHONE,
  beforeEach({ msw }) {
    msw.use(getListTableMaintenanceRunsMockHandler([queuedRun()]));
  },
  play: async ({ canvasElement }) => {
    await openRun(canvasElement, IN_FLIGHT_RUN_ID);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const Reconciliations: Story = {
  args: { route: `${ORDERS}/reconciliations` },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("button", { name: /^Started Rewrite data files/ })).toBeVisible();
    await expect(canvas.getByRole("button", { name: /^4 reconciliations found nothing to do/ })).toBeVisible();
    await expect(canvas.getByRole("button", { name: /^Would start Rewrite data files/ })).toHaveTextContent("Dry run");
    await expect(canvas.getByRole("button", { name: /^Skipped: table not found/ })).toBeVisible();
    await expect(canvas.getByRole("link", { name: `Open maintenance run ${SCHEDULED_RUN_ID}` })).toHaveTextContent(
      new RegExp(`^Run ${SCHEDULED_RUN_ID}$`),
    );
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
    await expect(drawer.getByRole("link", { name: `Open maintenance run ${SCHEDULED_RUN_ID}` })).toHaveAttribute(
      "href",
      `${ORDERS}/maintenance?run=${SCHEDULED_RUN_ID}`,
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

export const ReconciliationPolicyLink: Story = {
  args: { route: `${ORDERS}/reconciliations` },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const row = await canvas.findByRole("button", { name: /^Started Rewrite data files/ });
    await expect(row).toHaveTextContent("retail-nightly v4");
    await userEvent.click(row);
    const drawer = within(await within(canvasElement.ownerDocument.body).findByRole("dialog"));
    await expect(drawer.getByRole("link", { name: "retail-nightly v4" })).toHaveAttribute(
      "href",
      "/policies/retail-nightly/versions/4",
    );
    await expect(drawer.getByText(/inherited from namespace iceberg\.retail/)).toBeVisible();
  },
};

export const Policy: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const panel = within(await canvas.findByRole("region", { name: "Maintenance policy" }));
    await expect(await panel.findByRole("link", { name: "iceberg.retail" })).toBeVisible();
    await expect(panel.getByRole("link", { name: "retail-nightly v4" })).toBeVisible();
    await expect(panel.queryByRole("button", { name: "Detach" })).toBeNull();
    await expect(canvas.getByRole("region", { name: "Table" })).toBeVisible();
  },
};

export const PolicyDryRun: Story = {
  beforeEach({ msw }) {
    msw.use(getGetTableApplicableMaintenancePolicyMockHandler({ ...POLICIES[2]!, target: null }));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("Platform default")).toBeVisible();
    const header = within(canvas.getByRole("heading", { level: 1, name: "orders" }).closest("header") as HTMLElement);
    await expect(header.queryByText("Dry run")).toBeNull();
    const panel = within(canvas.getByRole("region", { name: "Maintenance policy" }));
    await expect(panel.getByText("Dry run")).toBeVisible();
  },
};

// The old Policy tab's URL lands on the Overview.
export const PolicyOldUrl: Story = {
  args: { route: `${ORDERS}/policy` },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("region", { name: "Maintenance policy" })).toBeVisible();
    await expect(canvas.getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
    await expect(canvas.queryByRole("tab", { name: "Policy" })).toBeNull();
  },
};

// A table maintenance has no record of still shows the policy that applies, asked by its name.
export const PolicyNotRecorded: Story = {
  beforeEach({ msw }) {
    msw.use(
      getListCoveredCatalogsMockHandler({ catalogs: [] }),
      apiError("get", "/v1/tables/:tableUuid", "table uuid-orders not found", 404),
    );
  },
  play: async ({ canvasElement }) => {
    const panel = within(await within(canvasElement).findByRole("region", { name: "Maintenance policy" }));
    await expect(await panel.findByRole("link", { name: "retail-nightly v4" })).toBeVisible();
    await expect(panel.getByRole("button", { name: "Attach policy" })).toBeVisible();
    await expect(within(canvasElement).getByText("this catalog is not covered by maintenance")).toBeVisible();
  },
};

export const PolicyPhone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByRole("region", { name: "Maintenance policy" });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const Properties: Story = {
  args: { route: `${ORDERS}/properties` },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const row = within((await canvas.findByText("write.target-file-size-bytes")).closest("tr") as HTMLElement);
    await expect(row.getByText("Modified")).toBeVisible();
    await expect(row.getByRole("button", { name: "Reset write.target-file-size-bytes" })).toBeEnabled();
    const forced = within(canvas.getByText("gc.enabled").closest("tr") as HTMLElement);
    await expect(forced.getByText("Forced by catalog")).toBeVisible();
    await expect(forced.queryByRole("button")).toBeNull();
    await expect(canvas.getByRole("button", { name: "Delete owner" })).toBeEnabled();
    await expect(canvas.getByText(/Defaults of Iceberg 1\.10\.1/)).toBeVisible();
  },
};

export const PropertiesModifiedOnly: Story = {
  args: { route: `${ORDERS}/properties` },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await canvas.findByText("commit.retry.num-retries");
    await userEvent.click(canvas.getByRole("switch", { name: "Show modified only" }));
    await expect(canvas.queryByText("commit.retry.num-retries")).toBeNull();
    await expect(canvas.getByText("owner")).toBeVisible();
  },
};

export const PropertiesResetAll: Story = {
  args: { route: `${ORDERS}/properties` },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("button", { name: "Reset all to default" }));
    const dialog = within(await screen.findByRole("alertdialog", { name: "Reset all to default" }));
    await expect(dialog.getByText("write.target-file-size-bytes")).toBeVisible();
    await expect(dialog.getByText("owner")).toBeVisible();
    await expect(dialog.getByRole("button", { name: "Reset all" })).toBeEnabled();
  },
};

export const PropertiesUnavailable: Story = {
  args: { route: `${ORDERS}/properties` },
  beforeEach({ msw }) {
    msw.use(
      apiError("get", "/v1/catalogs/:catalog/namespaces/:namespace/tables/:table/properties", "Polaris is unreachable"),
    );
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText(/Could not load properties: Polaris is unreachable/)).toBeVisible();
  },
};

export const PropertiesPhone: Story = {
  args: { route: `${ORDERS}/properties` },
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByText("write.target-file-size-bytes");
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const Unmanaged: Story = {
  beforeEach({ msw }) {
    msw.use(getGetTableMockHandler({ ...MAINTAINED_ORDERS, status: "unmanaged", matched_rule_id: null }));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("the discovery rules do not include this table")).toBeVisible();
    await expect(canvas.queryByRole("button", { name: /Pause|Resume/ })).toBeNull();
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
