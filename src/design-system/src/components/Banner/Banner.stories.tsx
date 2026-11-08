import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { expectNoHorizontalPageScroll } from "../../stories/assertions";
import { Banner } from "./Banner";

const meta = {
  title: "Components/Banner",
  component: Banner,
  args: { type: "information", title: "Heads up", children: "Maintenance runs at 02:00." },
  parameters: {
    docs: {
      description: {
        component:
          "Sizes are the same in both window classes. Backgrounds use the container and " +
          "on-container pairs; the type is always carried by the icon shape and the title.",
      },
    },
  },
} satisfies Meta<typeof Banner>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Information: Story = {
  play: async ({ canvasElement }) => {
    const banner = within(canvasElement).getByRole("status");
    await expect(banner).toHaveTextContent("Heads up");
  },
};

export const Notice: Story = {
  args: { type: "notice", title: "Falling behind", children: "Compaction is 3 runs late." },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("status")).toHaveTextContent("Falling behind");
  },
};

export const Positive: Story = {
  args: { type: "positive", title: "Done", children: "Snapshot expiry finished." },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("status")).toHaveTextContent("Done");
  },
};

export const Negative: Story = {
  args: { type: "negative", title: "Run failed", children: "The Spark driver exited with 1." },
  play: async ({ canvasElement }) => {
    const banner = within(canvasElement).getByRole("alert");
    await expect(banner).toHaveTextContent("Run failed");
    await expect(within(canvasElement).queryByRole("status")).toBeNull();
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  args: {
    type: "negative",
    title: "Run failed",
    children: "The Spark driver exited with a very long error message that has to wrap.",
  },
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
