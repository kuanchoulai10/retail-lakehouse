import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { apiError } from "@/stories/apiError";
import { ConsolePage } from "@/stories/ConsolePage";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";

const meta = {
  title: "Pages/Platform settings",
  component: ConsolePage,
  args: { route: "/platform-settings" },
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof ConsolePage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const capacity = await canvas.findByRole("region", { name: "Execution capacity" });
    await expect(within(capacity).getByText("Attempt time limit")).toBeVisible();
    await expect(within(capacity).getByText("6 h")).toBeVisible();
    await expect(within(capacity).getByText("21,600 seconds")).toBeVisible();
    for (const title of ["Spark sizes", "Cooldown and backoff", "Discovery"]) {
      await expect(canvas.getByRole("region", { name: title })).toBeVisible();
    }
    await expect(
      canvas.getByText("These values are set by the platform deployment; the console cannot change them."),
    ).toBeVisible();
    await expect(canvas.getByRole("link", { name: "Platform settings" })).toHaveAttribute("aria-current", "page");
  },
};

export const LoadError: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("get", "/v1/platform-settings", "settings unavailable", 500));
  },
  play: async ({ canvasElement }) => {
    await expect(
      await within(canvasElement).findByText("Could not load platform settings: settings unavailable"),
    ).toBeVisible();
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByRole("region", { name: "Discovery" });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
