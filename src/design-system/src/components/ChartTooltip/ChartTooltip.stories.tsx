import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { resolvedColor } from "../../stories/assertions";
import { CHART_COLOURS } from "../ChartContainer/ChartContainer";
import { ChartTooltip } from "./ChartTooltip";

const meta = {
  title: "Charts/ChartTooltip",
  component: ChartTooltip,
  args: {
    active: true,
    label: "06:10",
    payload: [
      { dataKey: "dataFiles", name: "Data files", value: 1194, color: CHART_COLOURS[0] },
      { dataKey: "positionDeletes", name: "Position deletes", value: 44, color: CHART_COLOURS[1] },
    ],
  },
  parameters: {
    docs: {
      description: {
        component:
          "No Serendie counterpart. The tooltip the charts show for the point under the " +
          "pointer or keyboard focus, on the inverse surface like `Tooltip`. Pass it to a " +
          "Recharts `Tooltip` as `content` when you build a chart the design system lacks.",
      },
    },
  },
} satisfies Meta<typeof ChartTooltip>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const tooltip = canvasElement.querySelector("[data-chart-tooltip]") as HTMLElement;
    await expect(tooltip).toHaveTextContent("06:10");
    await expect(within(tooltip).getAllByRole("listitem")[0]).toHaveTextContent("Data files1,194");
    await expect(getComputedStyle(tooltip).backgroundColor).toBe(resolvedColor("inverse-surface", canvasElement));
  },
};

export const Inactive: Story = {
  args: { active: false },
  play: async ({ canvasElement }) => {
    await expect(canvasElement.querySelector("[data-chart-tooltip]")).toBeNull();
  },
};
