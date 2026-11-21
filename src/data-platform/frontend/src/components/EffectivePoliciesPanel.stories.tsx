import type { Meta, StoryObj } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { expect, screen, userEvent, waitFor, within } from "storybook/test";
import { getGetEffectivePoliciesMockHandler } from "@/api/generated/tables/tables.msw";
import { apiError } from "@/stories/apiError";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";
import { effectivePolicies, POLICIES } from "@/stories/storyData";
import { EffectivePoliciesPanel } from "./EffectivePoliciesPanel";

const meta = {
  title: "Components/Effective policies panel",
  component: EffectivePoliciesPanel,
  args: { scope: { type: "namespace", catalog: "iceberg", namespace: ["retail"] } },
  decorators: [
    (Story) => (
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter>
          <div className="max-w-xl bg-surface p-4">
            <Story />
          </div>
        </MemoryRouter>
      </QueryClientProvider>
    ),
  ],
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof EffectivePoliciesPanel>;

export default meta;
type Story = StoryObj<typeof meta>;

async function rows(canvasElement: HTMLElement): Promise<HTMLElement[]> {
  const panel = await within(canvasElement).findByRole("region", { name: "Policies" });
  return within(panel).findAllByRole("listitem");
}

// Namespace iceberg.retail holds retail-nightly itself and takes core-tables from its catalog.
export const AttachedHere: Story = {
  play: async ({ canvasElement }) => {
    const [maintenance, discovery] = await rows(canvasElement);
    await expect(maintenance).toHaveTextContent("Attached here");
    await expect(within(maintenance!).getByRole("button", { name: "Detach maintenance policy" })).toBeVisible();
    await expect(within(maintenance!).getByRole("button", { name: "Replace maintenance policy" })).toBeVisible();
    await expect(discovery).toHaveTextContent("From catalog iceberg");
    await expect(within(discovery!).queryByRole("button", { name: "Detach discovery policy" })).toBeNull();
  },
};

export const Inherited: Story = {
  args: {
    scope: { type: "table", catalog: "iceberg", namespace: ["retail"], table: "orders", tableUuid: "uuid-orders", recorded: true },
  },
  play: async ({ canvasElement }) => {
    const [maintenance, discovery] = await rows(canvasElement);
    await expect(within(maintenance!).getByRole("link", { name: "iceberg.retail" })).toBeVisible();
    await expect(within(maintenance!).getByRole("link", { name: "retail-nightly v4" })).toBeVisible();
    await expect(within(discovery!).getByRole("link", { name: "core-tables v1" })).toBeVisible();
    await expect(within(discovery!).getByRole("link", { name: "iceberg" })).toBeVisible();
    await expect(within(canvasElement).queryByRole("button", { name: /^Detach/ })).toBeNull();
  },
};

export const PlatformDefaultInDryRun: Story = {
  args: { scope: { type: "catalog", catalog: "analytics" } },
  beforeEach({ msw }) {
    const [, discovery] = effectivePolicies("analytics").policies;
    const scratch = POLICIES[2]!;
    msw.use(
      getGetEffectivePoliciesMockHandler({
        policies: [
          {
            kind: "maintenance",
            policy_id: scratch.id,
            policy_name: scratch.name,
            version: scratch.version,
            description: scratch.description,
            dry_run: true,
            target: null,
            attachment_id: null,
          },
          discovery!,
        ],
      }),
    );
  },
  play: async ({ canvasElement }) => {
    const [maintenance, discovery] = await rows(canvasElement);
    await expect(within(maintenance!).getByText("Platform default")).toBeVisible();
    await expect(within(maintenance!).getByText("Dry run")).toBeVisible();
    await expect(within(discovery!).getByText("Platform default")).toBeVisible();
  },
};

export const LoadError: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("get", "/v1/effective-policies", "catalog iceberg not found", 404));
  },
  play: async ({ canvasElement }) => {
    await expect(await within(canvasElement).findByText(/catalog iceberg not found/)).toBeVisible();
    await expect(within(canvasElement).queryByRole("listitem")).toBeNull();
  },
};

export const DetachFails: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("delete", "/v1/maintenance-policies/:name/mappings", "database unavailable", 500));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("button", { name: "Detach maintenance policy" }));
    await expect(await canvas.findByText("Could not detach retail-nightly: database unavailable")).toBeVisible();
    await waitFor(() => expect(canvas.getByRole("button", { name: "Detach maintenance policy" })).toHaveFocus());
  },
};

// Tab reaches each row's buttons in order; Enter opens the dialog for that kind, Escape closes it
// and gives focus back to the button that opened it.
export const Keyboard: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const replace = await canvas.findByRole("button", { name: "Replace maintenance policy" });
    replace.focus();
    await userEvent.tab();
    await expect(canvas.getByRole("button", { name: "Detach maintenance policy" })).toHaveFocus();
    await userEvent.tab();
    await expect(canvas.getByRole("link", { name: "core-tables v1" })).toHaveFocus();
    await userEvent.tab();
    await expect(canvas.getByRole("link", { name: "iceberg" })).toHaveFocus();
    await userEvent.tab();
    const attachDiscovery = canvas.getByRole("button", { name: "Attach discovery policy" });
    await expect(attachDiscovery).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    const dialog = await screen.findByRole("dialog", { name: "Attach policy" });
    await userEvent.click(await within(dialog).findByRole("combobox", { name: "Policy" }));
    await expect(await screen.findByRole("option", { name: "sales-tables" })).toBeVisible();
    await expect(screen.queryByRole("option", { name: "retail-nightly" })).toBeNull();
    await userEvent.keyboard("{Escape}");
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(attachDiscovery).toHaveFocus());
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await rows(canvasElement);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
