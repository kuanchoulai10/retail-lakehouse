import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, waitFor } from "storybook/test";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { expectNoHorizontalPageScroll } from "../../stories/assertions";
import { CHART_COLOURS, ChartContainer } from "./ChartContainer";

const data = [
  { day: "Mon", appends: 12, overwrites: 1 },
  { day: "Tue", appends: 9, overwrites: 3 },
  { day: "Wed", appends: 14, overwrites: 0 },
];

const meta = {
  title: "Components/ChartContainer",
  component: ChartContainer,
  args: { label: "Commits per day", height: 240, children: <div /> },
  parameters: {
    docs: {
      description: {
        component:
          "No Serendie counterpart. Wraps Recharts' ResponsiveContainer with a fixed height and " +
          "exposes CHART_COLOURS for series. Sizes are the same in both window classes.",
      },
    },
  },
} satisfies Meta<typeof ChartContainer>;

export default meta;

type Story = StoryObj<typeof meta>;

const chart = (
  <BarChart data={data}>
    <CartesianGrid vertical={false} />
    <XAxis dataKey="day" />
    <YAxis width={32} />
    <Bar dataKey="appends" fill={CHART_COLOURS[0]} />
    <Bar dataKey="overwrites" fill={CHART_COLOURS[1]} />
  </BarChart>
);

export const Default: Story = {
  render: () => (
    <ChartContainer label="Commits per day" height={240}>
      {chart}
    </ChartContainer>
  ),
  play: async ({ canvasElement }) => {
    await waitFor(() => expect(canvasElement.querySelector("svg.recharts-surface")).not.toBeNull());
    const surface = canvasElement.querySelector("svg.recharts-surface") as SVGElement;
    await expect(surface.getBoundingClientRect().height).toBeGreaterThan(0);
    await expect(CHART_COLOURS).toHaveLength(5);
    await expect(CHART_COLOURS[0]).toBe("var(--color-chart-1)");
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  render: () => (
    <ChartContainer label="Commits per day" height={200}>
      {chart}
    </ChartContainer>
  ),
  play: async ({ canvasElement }) => {
    await waitFor(() => expect(canvasElement.querySelector("svg.recharts-surface")).not.toBeNull());
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
