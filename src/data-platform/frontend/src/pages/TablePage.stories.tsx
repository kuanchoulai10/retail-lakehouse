import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { getListCompactionCandidatesMockHandler } from "@/api/generated/compaction-candidates/compaction-candidates.msw";
import { getListCoveredCatalogsMockHandler } from "@/api/generated/discovery-rules/discovery-rules.msw";
import { getGetTableApplicableMaintenancePolicyMockHandler } from "@/api/generated/maintenance-policies/maintenance-policies.msw";
import { getListTableMaintenanceRunsMockHandler } from "@/api/generated/table-maintenance-runs/table-maintenance-runs.msw";
import { getGetTableHealthMockHandler, getGetTableMockHandler } from "@/api/generated/tables/tables.msw";
import { getListTableReconciliationsMockHandler } from "@/api/generated/table-reconciliations/table-reconciliations.msw";
import { temporalWorkflowsUrl } from "@/lib/temporalWorkflowsUrl";
import { apiError } from "@/stories/apiError";
import { ConsolePage } from "@/stories/ConsolePage";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";
import { ESCALATED_RUN, HEALTH, MAINTAINED_ORDERS, POLICIES } from "@/stories/storyData";

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

export const Maintenance: Story = {
  args: { route: `${ORDERS}/maintenance` },
  play: async ({ canvasElement }) => {
    const link = await within(canvasElement).findByRole("link", { name: "Running workflows in Temporal" });
    await expect(link).toHaveAttribute("href", temporalWorkflowsUrl(MAINTAINED_ORDERS.uuid));
  },
};

async function openEscalatedRun(canvasElement: HTMLElement) {
  const canvas = within(canvasElement);
  await userEvent.click(await canvas.findByRole("button", { name: "Expand run run-escalated" }));
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

export const Candidates: Story = {
  args: { route: `${ORDERS}/candidates` },
  play: async ({ canvasElement }) => {
    const table = within(await within(canvasElement).findByRole("table", { name: "Compaction candidates, best first" }));
    await expect(table.getByText("In run run-1")).toBeVisible();
    await expect(table.getByText("Still being written; checked again after a quiet period")).toBeVisible();
    await expect(table.getByText("Score below the top 2 (2 per run)")).toBeVisible();
    await expect(table.getByText("Too small to be worth compacting")).toBeVisible();
    await expect(table.getAllByText("Held")[0]).toHaveClass("bg-surface-container-dim");
  },
};

export const CandidatesEmpty: Story = {
  args: { route: `${ORDERS}/candidates` },
  beforeEach({ msw }) {
    msw.use(getListCompactionCandidatesMockHandler({ partitions_per_run: 10, candidates: [] }));
  },
  play: async ({ canvasElement }) => {
    await expect(await within(canvasElement).findByText("No partition needs compaction.")).toBeVisible();
  },
};

export const CandidatesPhone: Story = {
  args: { route: `${ORDERS}/candidates` },
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByRole("table", { name: "Compaction candidates, best first" });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const HealthNeedsAttention: Story = {
  beforeEach({ msw }) {
    msw.use(
      getGetTableHealthMockHandler({
        ...HEALTH,
        operations: HEALTH.operations.map((line) =>
          line.operation === "rewrite_data_files" ? { ...line, verdict: "needs_attention" } : line,
        ),
      }),
    );
  },
  play: async ({ canvasElement }) => {
    const line = await within(canvasElement).findByText(/^Needs attention: out of memory at the largest size/);
    await expect(line).toBeVisible();
    await expect(line).toHaveClass("text-negative-text");
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
  args: { route: `${ORDERS}/policy` },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const panel = within(await canvas.findByRole("region", { name: "Maintenance policy" }));
    await expect(await panel.findByRole("link", { name: "iceberg.retail" })).toBeVisible();
    await expect(panel.getByRole("link", { name: "retail-nightly v4" })).toBeVisible();
    await expect(panel.queryByRole("button", { name: "Detach" })).toBeNull();
  },
};

export const PolicyDryRun: Story = {
  args: { route: `${ORDERS}/policy` },
  beforeEach({ msw }) {
    msw.use(getGetTableApplicableMaintenancePolicyMockHandler({ ...POLICIES[2]!, target: null }));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("Platform default")).toBeVisible();
    const header = within(canvas.getByRole("heading", { level: 1, name: "orders" }).closest("header") as HTMLElement);
    await expect(header.getByText("Dry run")).toBeVisible();
  },
};

// A table maintenance has no record of still shows the policy that applies, asked by its name.
export const PolicyNotRecorded: Story = {
  args: { route: `${ORDERS}/policy` },
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
    await expect(within(canvasElement).queryByText("this catalog is not covered by maintenance")).toBeNull();
  },
};

export const PolicyPhone: Story = {
  args: { route: `${ORDERS}/policy` },
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByRole("region", { name: "Maintenance policy" });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const Properties: Story = { args: { route: `${ORDERS}/properties` } };

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
