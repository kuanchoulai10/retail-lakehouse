import type { Meta, StoryObj } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { expect, screen, userEvent, waitFor, within } from "storybook/test";
import {
  getDetachTableDiscoveryPolicyMockHandler,
  getListScannedCatalogsMockHandler,
  getListTableDiscoveryPolicyAttachmentsMockHandler,
} from "@/api/generated/discovery-policies/discovery-policies.msw";
import type { ListedTableDiscoveryPolicyAttachmentApiResponse } from "@/api/generated/model";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";
import { DISCOVERY_POLICY_ATTACHMENTS, SALES_TABLES_POLICY_ID } from "@/stories/storyData";
import { DiscoveryPolicyAttachments } from "./DiscoveryPolicyAttachments";

function attachment(
  id: string,
  type: string,
  path: string[],
  orphaned = false,
): ListedTableDiscoveryPolicyAttachmentApiResponse {
  return {
    id,
    policy_id: SALES_TABLES_POLICY_ID,
    policy_name: "sales-tables",
    target: { type, path, table_uuid: type === "table" ? "0b6e1c2a-5d3f-4f7e-8a90-1c2d3e4f5a6b" : null },
    orphaned,
    attached_at: "2026-11-05T09:00:00Z",
  };
}

// One target of each kind: analytics, where nothing manages tables, and two in iceberg, which
// discovery scans; the table has since been dropped.
const THREE_KINDS = [
  attachment("da-01m7s6c3tqee0rhg00xry2zqr0", "catalog", ["analytics"]),
  DISCOVERY_POLICY_ATTACHMENTS[0]!,
  attachment("da-01m7s6c3tqee0rhg00xry2zqr1", "table", ["iceberg", "finance", "ledger_2025_archive_with_a_long_name"], true),
];

const meta = {
  title: "Components/Discovery policy attachments",
  component: DiscoveryPolicyAttachments,
  args: { policyName: "sales-tables" },
  decorators: [
    (Story) => (
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter>
          <Story />
        </MemoryRouter>
      </QueryClientProvider>
    ),
  ],
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof DiscoveryPolicyAttachments>;

export default meta;
type Story = StoryObj<typeof meta>;

function row(name: string): HTMLElement {
  const item = screen.getByRole("button", { name: `Detach from ${name}` }).closest("li");
  if (item === null) throw new Error(`no row for ${name}`);
  return item;
}

export const Attached: Story = {
  beforeEach({ msw }) {
    msw.use(getListTableDiscoveryPolicyAttachmentsMockHandler({ attachments: THREE_KINDS }));
  },
  play: async () => {
    await screen.findByRole("button", { name: "Detach from analytics" });
    const catalog = within(row("analytics"));
    await expect(catalog.getByText("Catalog")).toBeVisible();
    await expect(catalog.getByRole("link", { name: "analytics" })).toBeVisible();
    await expect(await catalog.findByText(/^Not scanned: no policy in/)).toBeVisible();
    const namespace = within(row("iceberg.sales"));
    await expect(namespace.getByRole("link", { name: "iceberg.sales" })).toBeVisible();
    await expect(namespace.getByText(/^Scanned/)).toBeVisible();
    const table = within(row("iceberg.finance.ledger_2025_archive_with_a_long_name"));
    await expect(table.getByText("Table")).toBeVisible();
    await expect(table.getByText("Orphaned")).toBeVisible();
    await expect(table.queryByRole("link")).toBeNull();
  },
};

export const NotAttached: Story = {
  beforeEach({ msw }) {
    msw.use(getListTableDiscoveryPolicyAttachmentsMockHandler({ attachments: [] }));
  },
  play: async () => {
    await expect(
      await screen.findByText("Not attached. Attach it to a catalog, namespace or table to apply it."),
    ).toBeVisible();
  },
};

// Attach opens the dialog with Enter; Escape closes it and focus returns to Attach.
export const AttachDialog: Story = {
  play: async () => {
    await screen.findByRole("button", { name: "Detach from iceberg.sales" });
    const attach = screen.getByRole("button", { name: "Attach" });
    attach.focus();
    await userEvent.keyboard("{Enter}");
    const dialog = await screen.findByRole("dialog", { name: "Attach sales-tables" });
    await expect(within(dialog).getByRole("combobox", { name: "Type" })).toHaveTextContent("Catalog");
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(attach).toHaveFocus());
  },
};

// The platform's credential may not read iceberg: the row still lists, and says why the catalog is not scanned.
export const CannotAccess: Story = {
  beforeEach({ msw }) {
    msw.use(
      getListScannedCatalogsMockHandler({
        catalogs: [
          {
            catalog: "iceberg",
            last_discovered_at: "2026-11-08T08:10:00Z",
            failure: {
              reason: "cannot_access",
              detail: "the platform's catalog credential cannot read catalog iceberg",
              failed_at: "2026-11-09T08:10:00Z",
            },
          },
        ],
      }),
    );
  },
  play: async () => {
    await screen.findByRole("button", { name: "Detach from iceberg.sales" });
    const namespace = within(row("iceberg.sales"));
    await expect(await namespace.findByText("Cannot access")).toBeVisible();
    await expect(namespace.getByText(/the platform's catalog credential cannot read catalog iceberg/)).toBeVisible();
    await expect(namespace.queryByText("Orphaned")).toBeNull();
  },
};

// Detach by keyboard, without a confirmation; the row goes and focus lands on Attach.
export const Detach: Story = {
  beforeEach({ msw }) {
    let attachments = THREE_KINDS;
    msw.use(
      getListTableDiscoveryPolicyAttachmentsMockHandler(() => ({ attachments })),
      getDetachTableDiscoveryPolicyMockHandler(({ params }) => {
        attachments = attachments.filter((a) => a.id !== params.attachmentId);
      }),
    );
  },
  play: async () => {
    const detach = await screen.findByRole("button", { name: "Detach from analytics" });
    detach.focus();
    await userEvent.keyboard("{Enter}");
    await expect(screen.queryByRole("dialog")).toBeNull();
    await waitFor(() => expect(screen.queryByRole("button", { name: "Detach from analytics" })).toBeNull());
    await waitFor(() => expect(screen.getByRole("button", { name: "Attach" })).toHaveFocus());
  },
};

export const Phone: Story = {
  globals: PHONE,
  beforeEach({ msw }) {
    msw.use(getListTableDiscoveryPolicyAttachmentsMockHandler({ attachments: THREE_KINDS }));
  },
  play: async ({ canvasElement }) => {
    await screen.findByRole("button", { name: "Detach from analytics" });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
