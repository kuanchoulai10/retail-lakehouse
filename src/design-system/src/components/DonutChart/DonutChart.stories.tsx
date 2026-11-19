import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, waitFor, within } from "storybook/test";
import { expectNoHorizontalPageScroll } from "../../stories/assertions";
import { formatBytes } from "../../stories/chartSamples";
import { DonutChart } from "./DonutChart";

const SIZE_BY_KIND = [
  { name: "Data files", value: 3.1e9 },
  { name: "Delete files", value: 2.4e8 },
  { name: "Manifests", value: 6.2e7 },
  { name: "Metadata", value: 1.1e7 },
];

const meta = {
  title: "Charts/DonutChart",
  component: DonutChart,
  args: {
    label: "Storage by file kind",
    data: SIZE_BY_KIND,
    valueFormatter: formatBytes,
    centerLabel: formatBytes(SIZE_BY_KIND.reduce((total, slice) => total + slice.value, 0)),
  },
  parameters: {
    docs: {
      description: {
        component:
          "No Serendie counterpart. Parts of one whole, at most five parts (one per chart " +
          "colour). The legend lists every part with its value, so the numbers stay readable " +
          "without hovering. Sizes are the same in both window classes.",
      },
    },
  },
} satisfies Meta<typeof DonutChart>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    await waitFor(() => expect(canvasElement.querySelectorAll(".recharts-pie-sector")).toHaveLength(4));
    const legend = within(canvasElement).getByRole("list", { name: "Legend" });
    const rows = within(legend).getAllByRole("listitem");
    await expect(rows).toHaveLength(4);
    await expect(rows[0]).toHaveTextContent("Data files");
    await expect(rows[0]).toHaveTextContent("2.9 GB");
    await expect(within(canvasElement).getByText("3.2 GB")).toBeVisible();
  },
};

export const Loading: Story = {
  args: { loading: true },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("status")).toHaveTextContent("Loading chart");
  },
};

export const Empty: Story = {
  args: { data: [] },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("No data in this time range")).toBeVisible();
  },
};

export const Error: Story = {
  args: { error: "Couldn't load the storage breakdown." },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("alert")).toHaveTextContent("Couldn't load the storage breakdown.");
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  play: async ({ canvasElement }) => {
    await waitFor(() => expect(canvasElement.querySelectorAll(".recharts-pie-sector")).toHaveLength(4));
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
