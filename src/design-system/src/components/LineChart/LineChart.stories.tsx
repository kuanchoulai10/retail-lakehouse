import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, waitFor, within } from "storybook/test";
import { chartTooltip, expectFocusRing, expectNoHorizontalPageScroll } from "../../stories/assertions";
import { FILE_COUNTS, formatSampleTime } from "../../stories/chartSamples";
import { LineChart } from "./LineChart";

const SERIES = [
  { key: "dataFiles", name: "Data files" },
  { key: "positionDeletes", name: "Position deletes" },
  { key: "equalityDeletes", name: "Equality deletes" },
];

const meta = {
  title: "Charts/LineChart",
  component: LineChart,
  args: {
    label: "File counts over the last 6 hours",
    data: FILE_COUNTS,
    index: "time",
    series: SERIES,
    indexFormatter: formatSampleTime,
  },
  parameters: {
    docs: {
      description: {
        component:
          "No Serendie counterpart. A trend over time, one line per series, coloured from " +
          "CHART_COLOURS. The legend shows when there is more than one series. Focus the chart " +
          "and use the arrow keys to move the tooltip from point to point. Sizes are the same " +
          "in both window classes.",
      },
    },
  },
} satisfies Meta<typeof LineChart>;

export default meta;

type Story = StoryObj<typeof meta>;

async function rendered(canvasElement: HTMLElement): Promise<SVGElement> {
  await waitFor(() => expect(canvasElement.querySelector("svg.recharts-surface")).not.toBeNull());
  return canvasElement.querySelector("svg.recharts-surface") as SVGElement;
}

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await rendered(canvasElement);
    await expect(canvasElement.querySelectorAll(".recharts-line-curve")).toHaveLength(3);
    const legend = canvas.getByRole("list", { name: "Legend" });
    await expect(within(legend).getAllByRole("listitem").map((item) => item.textContent)).toEqual([
      "Data files",
      "Position deletes",
      "Equality deletes",
    ]);
    await userEvent.tab();
    const focused = canvasElement.ownerDocument.activeElement as HTMLElement;
    await expect(canvasElement).toContainElement(focused);
    await expectFocusRing(focused);
    const tooltip = await chartTooltip(canvasElement);
    await expect(tooltip).toHaveTextContent("06:00");
    await expect(tooltip).toHaveTextContent("Data files");
    await expect(tooltip).toHaveTextContent("1,180");
    await userEvent.keyboard("{ArrowRight}");
    await waitFor(() => expect(tooltip).toHaveTextContent("06:10"));
    await userEvent.keyboard("{ArrowLeft}");
    await waitFor(() => expect(tooltip).toHaveTextContent("06:00"));
  },
};

export const OneSeries: Story = {
  args: { series: [{ key: "dataFiles", name: "Data files" }] },
  play: async ({ canvasElement }) => {
    await rendered(canvasElement);
    await expect(canvasElement.querySelectorAll(".recharts-line-curve")).toHaveLength(1);
    await expect(within(canvasElement).queryByRole("list", { name: "Legend" })).toBeNull();
  },
};

export const Loading: Story = {
  args: { loading: true },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("status")).toHaveTextContent("Loading chart");
    await expect(canvasElement.querySelector("svg.recharts-surface")).toBeNull();
  },
};

export const Empty: Story = {
  args: { data: [] },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("No data in this time range")).toBeVisible();
    await expect(canvasElement.querySelector("svg.recharts-surface")).toBeNull();
  },
};

export const Error: Story = {
  args: { error: "Couldn't load the file counts. Try again in a minute." },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("alert")).toHaveTextContent("Couldn't load the file counts");
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
