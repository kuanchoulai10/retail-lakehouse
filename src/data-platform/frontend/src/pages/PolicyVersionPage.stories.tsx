import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { apiError } from "@/stories/apiError";
import { ConsolePage } from "@/stories/ConsolePage";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";

const meta = {
  title: "Pages/Policy version",
  component: ConsolePage,
  args: { route: "/policies/retail-nightly/versions/4" },
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof ConsolePage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("heading", { level: 1, name: "retail-nightly v4" })).toBeVisible();
    const data = within(canvas.getByRole("region", { name: "Rewrite data files" }));
    await expect(data.getByText("Whole table")).toBeVisible();
    await expect(data.getByText("Reducible files at least 20")).toBeVisible();
    await expect(canvas.queryByRole("textbox")).toBeNull();
  },
};

export const NotFound: Story = {
  args: { route: "/policies/retail-nightly/versions/9" },
  beforeEach({ msw }) {
    msw.use(apiError("get", "/v1/maintenance-policies/:name/versions/:version", "version 9 of retail-nightly not found", 404));
  },
  play: async ({ canvasElement }) => {
    await expect(
      await within(canvasElement).findByText("Could not load retail-nightly v9: version 9 of retail-nightly not found"),
    ).toBeVisible();
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByRole("heading", { level: 1, name: "retail-nightly v4" });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
