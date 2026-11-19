import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { CHART_COLOURS } from "../ChartContainer/ChartContainer";
import { ChartLegend } from "./ChartLegend";

const meta = {
  title: "Charts/ChartLegend",
  component: ChartLegend,
  args: {
    items: [
      { name: "Data files", colour: CHART_COLOURS[0] },
      { name: "Position deletes", colour: CHART_COLOURS[1] },
      { name: "Equality deletes", colour: CHART_COLOURS[2] },
    ],
  },
  parameters: {
    docs: {
      description: {
        component:
          "No Serendie counterpart. Names each series next to its colour; the charts render it " +
          "for you. With `value` it lists each part's value too, as the donut chart does.",
      },
    },
  },
} satisfies Meta<typeof ChartLegend>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const legend = within(canvasElement).getByRole("list", { name: "Legend" });
    await expect(within(legend).getAllByRole("listitem")).toHaveLength(3);
  },
};

export const WithValues: Story = {
  args: {
    className: "max-w-64 flex-col",
    items: [
      { name: "Data files", colour: CHART_COLOURS[0], value: "2.9 GB" },
      { name: "Delete files", colour: CHART_COLOURS[1], value: "229 MB" },
    ],
  },
  play: async ({ canvasElement }) => {
    const [first] = within(canvasElement).getAllByRole("listitem");
    await expect(first).toHaveTextContent("Data files2.9 GB");
  },
};
