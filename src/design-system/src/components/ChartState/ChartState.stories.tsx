import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { resolvedColor } from "../../stories/assertions";
import { ChartState } from "./ChartState";

const meta = {
  title: "Charts/ChartState",
  component: ChartState,
  args: { height: 160, children: <p>The chart goes here</p> },
  parameters: {
    docs: {
      description: {
        component:
          "No Serendie counterpart. Stands in for a chart while it loads, when it has no data " +
          "and when it could not load, at the chart's own height so the page does not jump. " +
          "The charts use it for you through `loading`, `error` and empty `data`.",
      },
    },
  },
} satisfies Meta<typeof ChartState>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Ready: Story = {
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("The chart goes here")).toBeVisible();
  },
};

export const Loading: Story = {
  args: { loading: true },
  play: async ({ canvasElement }) => {
    const status = within(canvasElement).getByRole("status");
    await expect(status).toHaveTextContent("Loading chart");
    await expect(status.getBoundingClientRect().height).toBe(160);
  },
};

export const Empty: Story = {
  args: { empty: true },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("No data in this time range")).toBeVisible();
    await expect(within(canvasElement).queryByText("The chart goes here")).toBeNull();
  },
};

export const Error: Story = {
  args: { error: "Couldn't load this chart. Try again in a minute." },
  play: async ({ canvasElement }) => {
    const alert = within(canvasElement).getByRole("alert");
    await expect(getComputedStyle(alert.firstElementChild as HTMLElement).color).toBe(
      resolvedColor("negative-text", canvasElement),
    );
  },
};
