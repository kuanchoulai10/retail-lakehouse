import type { Meta, StoryObj } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { expect, screen, userEvent, waitFor, within } from "storybook/test";
import { getGetApplicableMaintenancePolicyMockHandler } from "@/api/generated/maintenance-policies/maintenance-policies.msw";
import { apiError } from "@/stories/apiError";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";
import { applicablePolicy, POLICIES } from "@/stories/storyData";
import { ApplicablePolicyPanel } from "./ApplicablePolicyPanel";

const meta = {
  title: "Components/Applicable policy panel",
  component: ApplicablePolicyPanel,
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
} satisfies Meta<typeof ApplicablePolicyPanel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const AttachedHere: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("Attached here")).toBeVisible();
    await expect(canvas.getByRole("button", { name: "Detach" })).toBeVisible();
    await expect(canvas.getByRole("button", { name: "Replace policy" })).toBeVisible();
  },
};

export const Inherited: Story = {
  args: { scope: { type: "table", catalog: "iceberg", namespace: ["retail"], table: "orders", tableUuid: "uuid-orders", recorded: true } },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("link", { name: "iceberg.retail" })).toBeVisible();
    await expect(canvas.queryByRole("button", { name: "Detach" })).toBeNull();
  },
};

export const PlatformDefaultInDryRun: Story = {
  args: { scope: { type: "catalog", catalog: "iceberg" } },
  beforeEach({ msw }) {
    msw.use(getGetApplicableMaintenancePolicyMockHandler({ ...applicablePolicy("iceberg"), ...POLICIES[2]!, target: null }));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("Platform default")).toBeVisible();
    await expect(canvas.getByText("Dry run")).toBeVisible();
  },
};

export const LoadError: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("get", "/v1/applicable-policy", "database down"));
  },
  play: async ({ canvasElement }) => {
    await expect(await within(canvasElement).findByText(/database down/)).toBeVisible();
  },
};

// Opens with Enter, closes with Escape and gives focus back to the button that opened it.
export const AttachKeyboard: Story = {
  args: { scope: { type: "catalog", catalog: "iceberg" } },
  play: async ({ canvasElement }) => {
    const attach = await within(canvasElement).findByRole("button", { name: "Attach policy" });
    attach.focus();
    await userEvent.keyboard("{Enter}");
    const dialog = await screen.findByRole("dialog", { name: "Attach policy" });
    await expect(await within(dialog).findByRole("combobox", { name: "Policy" })).toBeVisible();
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(attach).toHaveFocus());
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByText("Attached here");
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
