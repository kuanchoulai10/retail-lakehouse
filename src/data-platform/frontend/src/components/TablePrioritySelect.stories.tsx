import type { Meta, StoryObj } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, screen, userEvent, waitFor, within } from "storybook/test";
import { apiError } from "@/stories/apiError";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";
import { MAINTAINED_ORDERS } from "@/stories/storyData";
import { TablePrioritySelect } from "./TablePrioritySelect";

const meta = {
  title: "Components/Table priority select",
  component: TablePrioritySelect,
  args: { table: MAINTAINED_ORDERS },
  decorators: [
    (Story) => (
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <div className="h-72 max-w-xl bg-surface p-4">
          <Story />
        </div>
      </QueryClientProvider>
    ),
  ],
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof TablePrioritySelect>;

export default meta;
type Story = StoryObj<typeof meta>;

// Tab to the select, open with Enter, arrows move, Escape closes and gives focus back.
export const Keyboard: Story = {
  play: async ({ canvasElement }) => {
    const trigger = within(canvasElement).getByRole("combobox", { name: "Priority" });
    await expect(trigger).toHaveTextContent("P3 · default");
    await userEvent.tab();
    await expect(trigger).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await waitFor(() => expect(screen.getByRole("option", { name: "P3 · default" })).toHaveFocus());
    await userEvent.keyboard("{ArrowUp}");
    await waitFor(() => expect(screen.getByRole("option", { name: "P2" })).toHaveFocus());
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("listbox")).toBeNull());
    await waitFor(() => expect(trigger).toHaveFocus());
    await userEvent.keyboard(" ");
    await screen.findByRole("listbox");
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("listbox")).toBeNull());
  },
};

export const Urgent: Story = {
  args: { table: { ...MAINTAINED_ORDERS, priority: "P0" } },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("combobox", { name: "Priority" })).toHaveTextContent("P0 · urgent");
  },
};

export const Dropped: Story = {
  args: { table: { ...MAINTAINED_ORDERS, status: "dropped", priority: "P1" } },
  play: async ({ canvasElement }) => {
    const trigger = within(canvasElement).getByRole("combobox", { name: "Priority" });
    await expect(trigger).toBeDisabled();
    await expect(trigger).toHaveTextContent("P1");
  },
};

export const SaveFails: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("put", "/v1/tables/:tableUuid/priority", "table is dropped", 409));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("combobox", { name: "Priority" }));
    await userEvent.click(await screen.findByRole("option", { name: "P1" }));
    await expect(await canvas.findByText(/Could not set the priority: table is dropped/)).toBeVisible();
    await expect(canvas.getByRole("combobox", { name: "Priority" })).toHaveTextContent("P3 · default");
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByRole("combobox", { name: "Priority" });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
