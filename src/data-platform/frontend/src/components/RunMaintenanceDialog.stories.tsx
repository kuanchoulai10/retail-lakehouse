import type { Meta, StoryObj } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, fn, screen, userEvent, waitFor, within } from "storybook/test";
import { getListTableMaintenanceRunsMockHandler } from "@/api/generated/table-maintenance-runs/table-maintenance-runs.msw";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { MAINTAINED_ORDERS, QUEUED_RUN } from "@/stories/storyData";
import { RunMaintenanceDialog } from "./RunMaintenanceDialog";

const meta = {
  title: "Components/Run maintenance dialog",
  component: RunMaintenanceDialog,
  args: { tableUuid: MAINTAINED_ORDERS.uuid, tablePriority: "P1", onClose: fn() },
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
} satisfies Meta<typeof RunMaintenanceDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const DefaultsToTablePriority: Story = {
  play: async () => {
    const dialog = await screen.findByRole("dialog", { name: "Run maintenance" });
    await expect(within(dialog).getByRole("combobox", { name: "Priority" })).toHaveTextContent("P1");
  },
};

export const PickPriority: Story = {
  play: async ({ args }) => {
    const dialog = await screen.findByRole("dialog", { name: "Run maintenance" });
    await userEvent.click(within(dialog).getByRole("combobox", { name: "Priority" }));
    await userEvent.click(await screen.findByRole("option", { name: "P0 · urgent" }));
    await waitFor(() => expect(within(dialog).getByRole("combobox", { name: "Priority" })).toHaveTextContent("P0 · urgent"));
    await userEvent.click(within(dialog).getByRole("button", { name: "Run" }));
    await waitFor(() => expect(args.onClose).toHaveBeenCalled());
  },
};

export const RunInFlight: Story = {
  beforeEach({ msw }) {
    msw.use(getListTableMaintenanceRunsMockHandler([QUEUED_RUN]));
  },
  play: async () => {
    const dialog = await screen.findByRole("dialog", { name: "Run maintenance" });
    await expect(await within(dialog).findByText(/^A maintenance run is already in flight\./)).toBeVisible();
    await expect(within(dialog).getByRole("button", { name: "Run" })).toBeEnabled();
  },
};
