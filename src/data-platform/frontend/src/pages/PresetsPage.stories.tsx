import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { getListTableMaintenancePresetsMockHandler } from "@/api/generated/table-maintenance-presets/table-maintenance-presets.msw";
import { apiError } from "@/stories/apiError";
import { ConsolePage } from "@/stories/ConsolePage";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";

const meta = {
  title: "Pages/Presets",
  component: ConsolePage,
  args: { route: "/presets" },
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof ConsolePage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    await expect(await within(canvasElement).findByText("preset-default")).toBeVisible();
  },
};

export const Empty: Story = {
  beforeEach({ msw }) {
    msw.use(getListTableMaintenancePresetsMockHandler([]));
  },
  play: async ({ canvasElement }) => {
    await expect(await within(canvasElement).findByText("No presets.")).toBeVisible();
  },
};

export const LoadError: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("get", "/v1/table-maintenance-presets", "database down", 500));
  },
};
