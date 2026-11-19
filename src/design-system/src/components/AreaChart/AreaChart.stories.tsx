import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, waitFor, within } from "storybook/test";
import { chartTooltip, expectFocusRing, expectNoHorizontalPageScroll } from "../../stories/assertions";
import { FILE_COUNTS, TOTAL_BYTES, formatBytes, formatSampleTime } from "../../stories/chartSamples";
import { AreaChart } from "./AreaChart";

const meta = {
  title: "Charts/AreaChart",
  component: AreaChart,
  args: {
    label: "Total size over the last 6 hours",
    data: TOTAL_BYTES,
    index: "time",
    series: [{ key: "bytes", name: "Total size" }],
    valueFormatter: formatBytes,
    indexFormatter: formatSampleTime,
  },
  parameters: {
    docs: {
      description: {
        component:
          "No Serendie counterpart. A trend whose area under the line matters, such as a size. " +
          "`stacked` stacks the series so the top line is their sum. Focus the chart and use " +
          "the arrow keys to move the tooltip. Sizes are the same in both window classes.",
      },
    },
  },
} satisfies Meta<typeof AreaChart>;

export default meta;

type Story = StoryObj<typeof meta>;

async function rendered(canvasElement: HTMLElement): Promise<void> {
  await waitFor(() => expect(canvasElement.querySelector("svg.recharts-surface")).not.toBeNull());
}

export const Default: Story = {
  play: async ({ canvasElement }) => {
    await rendered(canvasElement);
    await expect(canvasElement.querySelectorAll(".recharts-area-area")).toHaveLength(1);
    await userEvent.tab();
    await expectFocusRing(canvasElement.ownerDocument.activeElement as HTMLElement);
    const tooltip = await chartTooltip(canvasElement);
    await expect(tooltip).toHaveTextContent("06:00");
    await expect(tooltip).toHaveTextContent("3.0 GB");
    await userEvent.keyboard("{ArrowRight}");
    await waitFor(() => expect(tooltip).toHaveTextContent("06:10"));
  },
};

export const Stacked: Story = {
  args: {
    label: "Files by kind over the last 6 hours",
    data: FILE_COUNTS,
    series: [
      { key: "dataFiles", name: "Data files" },
      { key: "positionDeletes", name: "Position deletes" },
      { key: "equalityDeletes", name: "Equality deletes" },
    ],
    valueFormatter: undefined,
    stacked: true,
  },
  play: async ({ canvasElement }) => {
    await rendered(canvasElement);
    await expect(canvasElement.querySelectorAll(".recharts-area-area")).toHaveLength(3);
    await expect(within(canvasElement).getByRole("list", { name: "Legend" })).toBeVisible();
  },
};

export const Loading: Story = {
  args: { loading: true },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("status")).toHaveTextContent("Loading chart");
  },
};

export const Empty: Story = {
  args: { data: [], emptyText: "No size samples yet" },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("No size samples yet")).toBeVisible();
  },
};

export const Error: Story = {
  args: { error: "Couldn't load the table size." },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("alert")).toHaveTextContent("Couldn't load the table size.");
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  args: { height: 200 },
  play: async ({ canvasElement }) => {
    await rendered(canvasElement);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
