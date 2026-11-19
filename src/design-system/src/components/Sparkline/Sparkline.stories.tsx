import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, waitFor, within } from "storybook/test";
import { Sparkline } from "./Sparkline";

const RISING = [12, 14, 13, 17, 19, 18, 22, 25, 24, 28];

const meta = {
  title: "Charts/Sparkline",
  component: Sparkline,
  args: { label: "Data files, rising over the last 6 hours", data: RISING },
  parameters: {
    docs: {
      description: {
        component:
          "No Serendie counterpart. A small trend line with no axes or tooltip, for a metric " +
          "card or a table cell. It is an image: its label says what the trend shows. Sizes " +
          "are the same in both window classes.",
      },
    },
  },
  decorators: [(Story) => <div className="w-40">{Story()}</div>],
} satisfies Meta<typeof Sparkline>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const image = within(canvasElement).getByRole("img", { name: "Data files, rising over the last 6 hours" });
    await waitFor(() => expect(image.querySelector(".recharts-line-curve")).not.toBeNull());
    await expect(image.querySelector(".recharts-cartesian-axis")).toBeNull();
    await expect(image.querySelector("[tabindex='0']")).toBeNull();
  },
};

export const Area: Story = {
  args: { area: true },
  play: async ({ canvasElement }) => {
    await waitFor(() => expect(canvasElement.querySelector(".recharts-area-area")).not.toBeNull());
  },
};

export const Flat: Story = {
  args: { label: "Snapshots, unchanged", data: [4, 4, 4, 4, 4, 4] },
  play: async ({ canvasElement }) => {
    await waitFor(() => expect(canvasElement.querySelector(".recharts-line-curve")).not.toBeNull());
  },
};
