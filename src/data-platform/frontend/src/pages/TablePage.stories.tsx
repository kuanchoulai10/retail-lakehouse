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
import { DESKTOP, PHONE } from "@/stories/phone";
import {
  ESCALATED_RUN,
  ESCALATED_RUN_ID,
  inFlightRun,
  IN_FLIGHT_RUN_ID,
  MAINTAINED_ORDERS,
  OLDER_RUN_ID,
  ORDERS_HOURLY_SPEC_COMPARISON,
  ORDERS_HOURLY_SPEC_VERSIONS,
  ordersManySchemaVersions,
  ordersSchemaComparison,
  PARTITION_SCOPE_RUN,
  PARTITION_SCOPE_RUN_ID,
  PENDING_RUN_ID,
  pendingRun,
  POLICIES,
  QUEUE_TIMEOUT_RUN,
  QUEUE_TIMEOUT_RUN_ID,
  queuedRun,
  SCHEDULED_ORPHANS_RUN_ID,
  SCHEDULED_RECONCILIATION_ID,
  SCHEDULED_RUN_ID,
} from "@/stories/storyData";

const ORDERS = "/catalogs/iceberg/namespaces/retail/tables/orders";
const SCHEDULED_ROW = /^Started Rewrite data files.*retail-nightly v4/;
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

export const CommitsSchemaLink: Story = {
  args: { route: `${ORDERS}/commits` },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click((await canvas.findAllByRole("link", { name: "Schema v0" }))[0] as HTMLElement);
    const schema = within(await canvas.findByRole("region", { name: "Schema" }));
    await expect(await versionButton(schema, "v0")).toHaveAttribute("aria-current", "true");
    await expect(await schema.findByRole("list", { name: "Changes in schema v0" })).toBeVisible();
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
  globals: DESKTOP,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const link = await canvas.findByRole("link", { name: "Running workflows in Temporal" });
    await expect(link).toHaveAttribute("href", temporalWorkflowsUrl(MAINTAINED_ORDERS.uuid));
    const runs = canvas.getByRole("table", { name: "Maintenance runs, newest first" });
    await expect(
      within(runs)
        .getAllByRole("row")
        .slice(1)
        .map((row) => within(row).getAllByRole("cell")[0]!.textContent),
    ).toEqual(["Remove orphan files", "Expire snapshots", "Rewrite manifests", "Rewrite data files"]);
  },
};

// The run's side panel, opened through its url as a reconciliation's link opens it.
async function openedRun(canvasElement: HTMLElement, name: string) {
  return within(await within(canvasElement.ownerDocument.body).findByRole("dialog", { name }));
}

function maintenanceRoute(runId: string) {
  return `${ORDERS}/maintenance?run=${runId}`;
}

export const MaintenanceRunPanel: Story = {
  args: { route: `${ORDERS}/maintenance` },
  globals: DESKTOP,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const runs = await canvas.findByRole("region", { name: "Maintenance runs, newest first" });
    runs.focus();
    await userEvent.tab();
    const open = canvas.getByRole("button", { name: `Open Remove orphan files run ${SCHEDULED_ORPHANS_RUN_ID}` });
    await expect(open).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    const panel = await openedRun(canvasElement, "Remove orphan files");
    await waitFor(() => expect(panel.getByRole("heading", { name: "Remove orphan files" })).toHaveFocus());
    await expect(panel.getByText(SCHEDULED_ORPHANS_RUN_ID)).toBeVisible();
    await expect(canvasElement.ownerDocument.body.querySelector(".bg-scrim")).toBeNull();
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(within(canvasElement.ownerDocument.body).queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(open).toHaveFocus());
  },
};

export const MaintenanceRunPanelPhone: Story = {
  args: { route: maintenanceRoute(SCHEDULED_RUN_ID) },
  globals: PHONE,
  play: async ({ canvasElement }) => {
    const panel = await within(canvasElement.ownerDocument.body).findByRole("dialog", { name: "Rewrite data files" });
    await expect(panel.getBoundingClientRect().width).toBe(window.innerWidth);
    await expect(within(panel).getByText("spec 0: (`region` = 'eu')")).toBeVisible();
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const MaintenanceAttemptsEscalated: Story = {
  args: { route: maintenanceRoute(ESCALATED_RUN_ID) },
  globals: DESKTOP,
  beforeEach({ msw }) {
    msw.use(getListTableMaintenanceRunsMockHandler([ESCALATED_RUN]));
  },
  play: async ({ canvasElement }) => {
    const panel = await openedRun(canvasElement, "Rewrite data files");
    const attempts = within(panel.getByRole("list", { name: "Attempts" }));
    await expect(attempts.getByText("Attempt 1 · S")).toBeVisible();
    await expect(attempts.getByText("Out of memory")).toBeVisible();
    await expect(attempts.getByText("Event log: Did not finish")).toBeVisible();
    await expect(attempts.getByText("Retrying at size M")).toBeVisible();
    await expect(attempts.getByText("Attempt 2 · M")).toBeVisible();
    await expect(attempts.getByText("Done")).toBeVisible();
  },
};

export const MaintenanceAttemptsEscalatedPhone: Story = {
  args: { route: maintenanceRoute(ESCALATED_RUN_ID) },
  globals: PHONE,
  beforeEach({ msw }) {
    msw.use(getListTableMaintenanceRunsMockHandler([ESCALATED_RUN]));
  },
  play: async ({ canvasElement }) => {
    await openedRun(canvasElement, "Rewrite data files");
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const MaintenanceAttemptRunning: Story = {
  args: { route: maintenanceRoute(IN_FLIGHT_RUN_ID) },
  globals: DESKTOP,
  beforeEach({ msw }) {
    msw.use(getListTableMaintenanceRunsMockHandler([inFlightRun()]));
  },
  play: async ({ canvasElement }) => {
    const panel = await openedRun(canvasElement, "Rewrite data files");
    await expect(panel.getByText(/^Ran .*\(running\)$/)).toBeVisible();
    await expect(panel.getByText("Out of memory")).toBeVisible();
  },
};

export const MaintenanceAttemptQueued: Story = {
  args: { route: maintenanceRoute(IN_FLIGHT_RUN_ID) },
  globals: DESKTOP,
  beforeEach({ msw }) {
    msw.use(getListTableMaintenanceRunsMockHandler([queuedRun()]));
  },
  play: async ({ canvasElement }) => {
    const panel = await openedRun(canvasElement, "Rewrite data files");
    await expect(panel.getByText(/^Queued .*\(waiting\)$/)).toBeVisible();
  },
};

export const MaintenanceQueueTimeout: Story = {
  args: { route: maintenanceRoute(QUEUE_TIMEOUT_RUN_ID) },
  globals: DESKTOP,
  beforeEach({ msw }) {
    msw.use(getListTableMaintenanceRunsMockHandler([QUEUE_TIMEOUT_RUN]));
  },
  play: async ({ canvasElement }) => {
    const panel = await openedRun(canvasElement, "Rewrite data files");
    await expect(panel.getByText("Waited too long in the queue")).toBeVisible();
    await expect(panel.getByText("Queued 24h 0m")).toBeVisible();
  },
};

export const MaintenanceQueuedPhone: Story = {
  args: { route: maintenanceRoute(IN_FLIGHT_RUN_ID) },
  globals: PHONE,
  beforeEach({ msw }) {
    msw.use(getListTableMaintenanceRunsMockHandler([queuedRun()]));
  },
  play: async ({ canvasElement }) => {
    await openedRun(canvasElement, "Rewrite data files");
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const MaintenancePartitionScope: Story = {
  args: { route: maintenanceRoute(PARTITION_SCOPE_RUN_ID) },
  globals: DESKTOP,
  beforeEach({ msw }) {
    msw.use(getListTableMaintenanceRunsMockHandler([PARTITION_SCOPE_RUN, ESCALATED_RUN]));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const panel = await openedRun(canvasElement, "Rewrite data files");
    await expect(panel.getByText("Partitions over the target")).toBeVisible();
    await expect(panel.getByText(/^spec 0: .*DATE '2026-11-19'\)$/)).toBeVisible();
    await expect(panel.getByText(/^spec 1: /)).toBeVisible();
    await userEvent.click(canvas.getByRole("button", { name: `Open Rewrite data files run ${ESCALATED_RUN_ID}` }));
    await expect(await panel.findByText("Whole table")).toBeVisible();
    await expect(panel.queryByText("Partitions over the target")).toBeNull();
    await expect(within(canvasElement.ownerDocument.body).getAllByRole("dialog")).toHaveLength(1);
  },
};

export const MaintenancePartitionScopePhone: Story = {
  args: { route: maintenanceRoute(PARTITION_SCOPE_RUN_ID) },
  globals: PHONE,
  beforeEach({ msw }) {
    msw.use(getListTableMaintenanceRunsMockHandler([PARTITION_SCOPE_RUN, ESCALATED_RUN]));
  },
  play: async ({ canvasElement }) => {
    const panel = await openedRun(canvasElement, "Rewrite data files");
    await expect(panel.getByText("Partitions over the target")).toBeVisible();
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

// A run older than the latest 50 the list returns opens through the read by id.
export const MaintenanceOlderRunLink: Story = {
  args: { route: maintenanceRoute(OLDER_RUN_ID) },
  globals: DESKTOP,
  play: async ({ canvasElement }) => {
    const panel = await openedRun(canvasElement, "Expire snapshots");
    await expect(await panel.findByText(OLDER_RUN_ID)).toBeVisible();
    await expect(panel.getByText("retain_last")).toBeVisible();
  },
};

export const MaintenanceRunGone: Story = {
  args: { route: maintenanceRoute("mr-01m000000000000000000000zz") },
  globals: DESKTOP,
  play: async ({ canvasElement }) => {
    const panel = await openedRun(canvasElement, "Maintenance run");
    await expect(await panel.findByText("This run is no longer available")).toBeVisible();
  },
};

// A plan in flight: its compaction runs, and the expiry after it waits pending, listed above it.
export const MaintenancePlanInFlight: Story = {
  args: { route: maintenanceRoute(PENDING_RUN_ID) },
  globals: DESKTOP,
  beforeEach({ msw }) {
    const now = new Date();
    msw.use(getListTableMaintenanceRunsMockHandler([pendingRun(now), inFlightRun(now)]));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const rows = within(await canvas.findByRole("table", { name: "Maintenance runs, newest first" }))
      .getAllByRole("row")
      .slice(1);
    await expect(within(rows[0]!).getByText("Expire snapshots")).toBeVisible();
    await expect(within(rows[0]!).getByText("Pending")).toBeVisible();
    await expect(within(rows[1]!).getByText("Rewrite data files")).toBeVisible();
    await expect(within(rows[1]!).getByText("Running")).toBeVisible();
    const panel = await openedRun(canvasElement, "Expire snapshots");
    await expect(panel.getByText("No attempt yet. This run waits for the runs before it.")).toBeVisible();
  },
};

export const Reconciliations: Story = {
  args: { route: `${ORDERS}/reconciliations` },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("button", { name: SCHEDULED_ROW })).toBeVisible();
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

// The reconciliation's side panel, opened through its url as a link to it opens it.
function reconciliationRoute(id: string) {
  return `${ORDERS}/reconciliations?reconciliation=${id}`;
}

export const ReconciliationDrawer: Story = {
  args: { route: reconciliationRoute(SCHEDULED_RECONCILIATION_ID) },
  globals: DESKTOP,
  play: async ({ canvasElement }) => {
    const drawer = within(await within(canvasElement.ownerDocument.body).findByRole("dialog"));
    await expect(drawer.getByRole("heading", { level: 2, name: "Started Rewrite data files" })).toBeVisible();
    await expect(drawer.getByText(/Catalog commit × 3/)).toBeVisible();
    // Each operation links the run it started; only the compaction started one here.
    const compaction = within(drawer.getByRole("region", { name: "Rewrite data files" }));
    await expect(compaction.getByRole("link", { name: `Open maintenance run ${SCHEDULED_RUN_ID}` })).toHaveAttribute(
      "href",
      `${ORDERS}/maintenance?run=${SCHEDULED_RUN_ID}`,
    );
    await expect(drawer.getAllByRole("link", { name: /^Open maintenance run/ })).toHaveLength(1);
    const measurements = drawer.getAllByRole("button", { name: "All measurements" })[0]!;
    await userEvent.click(measurements);
    await expect(measurements).toHaveAttribute("aria-expanded", "true");
    await expect(drawer.getByRole("list", { name: "All measurements of Rewrite data files" })).toBeVisible();
  },
};

export const ReconciliationPanelKeyboard: Story = {
  args: { route: `${ORDERS}/reconciliations` },
  globals: DESKTOP,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const body = within(canvasElement.ownerDocument.body);
    const first = await canvas.findByRole("button", { name: SCHEDULED_ROW });
    first.focus();
    await userEvent.keyboard("{Enter}");
    await body.findByRole("dialog", { name: "Started Rewrite data files" });
    await waitFor(() => expect(body.getByRole("heading", { name: "Started Rewrite data files" })).toHaveFocus());
    await expect(canvasElement.ownerDocument.body.querySelector(".bg-scrim")).toBeNull();
    const next = canvas.getByRole("button", { name: /^Would start Rewrite data files/ });
    await userEvent.click(next);
    await expect(body.getAllByRole("dialog")).toHaveLength(1);
    await body.findByRole("dialog", { name: "Would start Rewrite data files" });
    await waitFor(() => expect(body.getByRole("heading", { name: "Would start Rewrite data files" })).toHaveFocus());
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(body.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(next).toHaveFocus());
  },
};

export const ReconciliationPanelPhone: Story = {
  args: { route: reconciliationRoute(SCHEDULED_RECONCILIATION_ID) },
  globals: PHONE,
  play: async ({ canvasElement }) => {
    const panel = await within(canvasElement.ownerDocument.body).findByRole("dialog", { name: "Started Rewrite data files" });
    await expect(panel.getBoundingClientRect().width).toBe(window.innerWidth);
    await expect(within(panel).getByText(/Catalog commit × 3/)).toBeVisible();
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const ReconciliationCappedRun: Story = {
  args: { route: `${ORDERS}/reconciliations` },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("button", { name: /^Started Rewrite data files.*default v1/ }));
    const drawer = within(await within(canvasElement.ownerDocument.body).findByRole("dialog"));
    await expect(
      drawer.getByText(/This run compacts 10 of them; 3 are still being written\./),
    ).toBeVisible();
  },
};

export const ReconciliationWaitingForWrites: Story = {
  args: { route: `${ORDERS}/reconciliations` },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("button", { name: /^Nothing to do/ }));
    const drawer = within(await within(canvasElement.ownerDocument.body).findByRole("dialog"));
    await expect(drawer.getByText("Waiting for writes")).toBeVisible();
    await expect(
      drawer.getByText(/but every partition over the target is still being written; next allowed Nov 10, \d\d:47\./),
    ).toBeVisible();
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
    await within(canvasElement).findByRole("button", { name: SCHEDULED_ROW });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const ReconciliationPolicyLink: Story = {
  args: { route: `${ORDERS}/reconciliations` },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const row = await canvas.findByRole("button", { name: SCHEDULED_ROW });
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
