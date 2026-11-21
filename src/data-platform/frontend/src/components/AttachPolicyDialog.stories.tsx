import type { Meta, StoryObj } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, fn, screen, userEvent, waitFor, within } from "storybook/test";
import { getListTableMaintenancePoliciesMockHandler } from "@/api/generated/maintenance-policies/maintenance-policies.msw";
import { apiError } from "@/stories/apiError";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";
import { POLICIES } from "@/stories/storyData";
import { AttachPolicyDialog } from "./AttachPolicyDialog";

const meta = {
  title: "Components/Attach policy dialog",
  component: AttachPolicyDialog,
  args: { kind: "maintenance", scope: { type: "namespace", catalog: "iceberg", namespace: ["retail"] }, current: null, onClose: fn() },
  decorators: [
    (Story) => (
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <Story />
      </QueryClientProvider>
    ),
  ],
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof AttachPolicyDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Attach: Story = {
  play: async ({ args }) => {
    const dialog = await screen.findByRole("dialog", { name: "Attach policy" });
    await userEvent.click(await within(dialog).findByRole("combobox", { name: "Policy" }));
    await userEvent.click(await screen.findByRole("option", { name: "scratch" }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Attach" }));
    await waitFor(() => expect(args.onClose).toHaveBeenCalled());
  },
};

export const NothingChosen: Story = {
  play: async ({ args }) => {
    const dialog = await screen.findByRole("dialog", { name: "Attach policy" });
    await within(dialog).findByRole("combobox", { name: "Policy" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Attach" }));
    await expect(await within(dialog).findByText("Choose a policy to attach.")).toBeVisible();
    await expect(args.onClose).not.toHaveBeenCalled();
  },
};

export const Replace: Story = {
  args: { current: "retail-nightly" },
  play: async () => {
    const dialog = await screen.findByRole("dialog", { name: "Replace policy" });
    await userEvent.click(await within(dialog).findByRole("combobox", { name: "Policy" }));
    await expect(screen.queryByRole("option", { name: "retail-nightly" })).toBeNull();
    await userEvent.keyboard("{Escape}");
  },
};

export const NoOtherPolicy: Story = {
  args: { current: "default" },
  beforeEach({ msw }) {
    msw.use(getListTableMaintenancePoliciesMockHandler({ policies: [POLICIES[0]!] }));
  },
  play: async () => {
    await expect(await screen.findByText("There is no other maintenance policy to attach.")).toBeVisible();
  },
};

// A discovery policy is picked from the discovery policies and attached through their route.
export const AttachDiscovery: Story = {
  args: { kind: "discovery" },
  play: async ({ args }) => {
    const dialog = await screen.findByRole("dialog", { name: "Attach policy" });
    await expect(dialog).toHaveTextContent("Attaches a discovery policy to the namespace iceberg.retail.");
    await userEvent.click(await within(dialog).findByRole("combobox", { name: "Policy" }));
    await expect(screen.queryByRole("option", { name: "retail-nightly" })).toBeNull();
    await userEvent.click(await screen.findByRole("option", { name: "sales-tables" }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Attach" }));
    await waitFor(() => expect(args.onClose).toHaveBeenCalled());
  },
};

export const ReplaceDiscovery: Story = {
  args: { kind: "discovery", current: "core-tables" },
  play: async () => {
    const dialog = await screen.findByRole("dialog", { name: "Replace policy" });
    await userEvent.click(await within(dialog).findByRole("combobox", { name: "Policy" }));
    await expect(await screen.findByRole("option", { name: "sales-tables" })).toBeVisible();
    await expect(screen.queryByRole("option", { name: "core-tables" })).toBeNull();
    await userEvent.keyboard("{Escape}");
  },
};

export const AttachDiscoveryFails: Story = {
  args: { kind: "discovery" },
  beforeEach({ msw }) {
    msw.use(apiError("put", "/v1/discovery-policies/sales-tables/attachments", "the platform cannot read catalog iceberg", 403));
  },
  play: async ({ args }) => {
    const dialog = await screen.findByRole("dialog", { name: "Attach policy" });
    await userEvent.click(await within(dialog).findByRole("combobox", { name: "Policy" }));
    await userEvent.click(await screen.findByRole("option", { name: "sales-tables" }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Attach" }));
    await expect(await within(dialog).findByText("the platform cannot read catalog iceberg")).toBeVisible();
    await expect(args.onClose).not.toHaveBeenCalled();
  },
};

export const AttachFails: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("put", "/v1/maintenance-policies/scratch/mappings", "namespace iceberg.retail not found", 404));
  },
  play: async ({ args }) => {
    const dialog = await screen.findByRole("dialog", { name: "Attach policy" });
    await userEvent.click(await within(dialog).findByRole("combobox", { name: "Policy" }));
    await userEvent.click(await screen.findByRole("option", { name: "scratch" }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Attach" }));
    await expect(await within(dialog).findByText("namespace iceberg.retail not found")).toBeVisible();
    await expect(args.onClose).not.toHaveBeenCalled();
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await screen.findByRole("dialog", { name: "Attach policy" });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
