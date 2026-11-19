import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, waitFor, within } from "storybook/test";
import { expectNoHorizontalPageScroll, resolvedColor } from "../../stories/assertions";
import { MetricCard } from "./MetricCard";

const meta = {
  title: "Charts/MetricCard",
  component: MetricCard,
  args: {
    label: "Data files",
    value: "1,684",
    delta: { text: "+504 in 6h", direction: "up", tone: "negative" },
    trend: [1180, 1250, 1320, 1390, 1460, 1530, 1600, 1684],
    trendLabel: "Data files, rising over the last 6 hours",
  },
  parameters: {
    docs: {
      description: {
        component:
          "No Serendie counterpart (a KPI card). The value now, with an optional change and a " +
          "sparkline. The change's colour says whether it is good or bad, set by `tone`, since " +
          "more is not always better: more small files is bad. Sizes are the same in both " +
          "window classes.",
      },
    },
  },
  decorators: [(Story) => <div className="max-w-72">{Story()}</div>],
} satisfies Meta<typeof MetricCard>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const card = canvas.getByRole("group", { name: "Data files" });
    await expect(within(card).getByText("1,684")).toBeVisible();
    const delta = within(card).getByText("+504 in 6h");
    await expect(getComputedStyle(delta.parentElement as HTMLElement).color).toBe(
      resolvedColor("negative-text", canvasElement),
    );
    await waitFor(() =>
      expect(within(card).getByRole("img", { name: "Data files, rising over the last 6 hours" })).toBeVisible(),
    );
  },
};

export const GoodChange: Story = {
  args: {
    label: "Reducible files",
    value: "12",
    delta: { text: "−480 in 6h", direction: "down", tone: "positive" },
    trend: [420, 440, 470, 492, 40, 22, 15, 12],
    trendLabel: "Reducible files, dropping after compaction",
  },
  play: async ({ canvasElement }) => {
    const delta = within(canvasElement).getByText("−480 in 6h");
    await expect(getComputedStyle(delta.parentElement as HTMLElement).color).toBe(
      resolvedColor("positive-text", canvasElement),
    );
  },
};

export const ValueOnly: Story = {
  args: { label: "Snapshots", value: "37", delta: undefined, trend: undefined },
  play: async ({ canvasElement }) => {
    const card = within(canvasElement).getByRole("group", { name: "Snapshots" });
    await expect(within(card).queryByRole("img")).toBeNull();
  },
};

export const NoChange: Story = {
  args: {
    label: "Manifests",
    value: "18",
    delta: { text: "No change in 6h", direction: "flat", tone: "neutral" },
    trend: [18, 18, 18, 18, 18, 18],
    trendLabel: "Manifests, unchanged",
  },
  play: async ({ canvasElement }) => {
    const delta = within(canvasElement).getByText("No change in 6h");
    await expect(getComputedStyle(delta.parentElement as HTMLElement).color).toBe(
      resolvedColor("on-surface-variant", canvasElement),
    );
  },
};

export const Loading: Story = {
  args: { loading: true },
  play: async ({ canvasElement }) => {
    const card = within(canvasElement).getByRole("group", { name: "Data files" });
    await expect(within(card).getByRole("status")).toHaveTextContent("Loading");
    await expect(within(card).queryByText("1,684")).toBeNull();
  },
};

export const Row: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  decorators: [(Story) => <div className="grid grid-cols-[repeat(auto-fit,minmax(10rem,1fr))] gap-3">{Story()}</div>],
  render: (args) => (
    <>
      <MetricCard {...args} />
      <MetricCard label="Total size" value="3.2 GB" delta={{ text: "+8% in 6h", direction: "up", tone: "neutral" }} />
      <MetricCard label="Snapshots" value="37" />
    </>
  ),
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getAllByRole("group")).toHaveLength(3);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
