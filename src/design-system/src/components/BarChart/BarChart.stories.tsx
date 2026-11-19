import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, waitFor, within } from "storybook/test";
import { chartTooltip, expectFocusRing, expectNoHorizontalPageScroll } from "../../stories/assertions";
import { COMMITS_PER_HOUR } from "../../stories/chartSamples";
import { BarChart } from "./BarChart";

const meta = {
  title: "Charts/BarChart",
  component: BarChart,
  args: {
    label: "Commits per hour",
    data: COMMITS_PER_HOUR,
    index: "hour",
    series: [
      { key: "appends", name: "Appends" },
      { key: "overwrites", name: "Overwrites" },
    ],
  },
  parameters: {
    docs: {
      description: {
        component:
          "No Serendie counterpart. Counts per bucket, side by side or `stacked`. Focus the " +
          "chart and use the arrow keys to move the tooltip from bar to bar. Sizes are the " +
          "same in both window classes.",
      },
    },
  },
} satisfies Meta<typeof BarChart>;

export default meta;

type Story = StoryObj<typeof meta>;

async function rendered(canvasElement: HTMLElement): Promise<void> {
  await waitFor(() => expect(canvasElement.querySelector("svg.recharts-surface")).not.toBeNull());
  await waitFor(() => expect(canvasElement.querySelectorAll(".recharts-bar-rectangle").length).toBeGreaterThan(0));
}

export const Default: Story = {
  play: async ({ canvasElement }) => {
    await rendered(canvasElement);
    // 6 hours x 2 series, less the hour with no overwrites: a zero bar draws nothing.
    await expect(canvasElement.querySelectorAll(".recharts-bar-rectangle")).toHaveLength(11);
    await userEvent.tab();
    await expectFocusRing(canvasElement.ownerDocument.activeElement as HTMLElement);
    const tooltip = await chartTooltip(canvasElement);
    await expect(tooltip).toHaveTextContent("06:00");
    await expect(tooltip).toHaveTextContent("Appends12");
    await userEvent.keyboard("{ArrowRight}");
    await waitFor(() => expect(tooltip).toHaveTextContent("07:00"));
  },
};

export const Stacked: Story = {
  args: { stacked: true },
  play: async ({ canvasElement }) => {
    await rendered(canvasElement);
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
  args: { data: [] },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("No data in this time range")).toBeVisible();
  },
};

export const Error: Story = {
  args: { error: "Couldn't load the commits." },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("alert")).toHaveTextContent("Couldn't load the commits.");
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
