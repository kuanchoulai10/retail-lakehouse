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

// retail-nightly: checked once a day, not after commits, compacting whole tables with a sort.
export const WithoutCatalogCommits: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("heading", { level: 1, name: "retail-nightly v4" })).toBeVisible();
    await expect(within(canvas.getByRole("region", { name: "Policy" })).getByText("Every 1 d")).toBeVisible();
    const data = within(canvas.getByRole("region", { name: "Rewrite data files" }));
    await expect(data.getByText("Reducible files at most 20, across the table")).toBeVisible();
    await expect(data.getByText("order_date DESC NULLS LAST")).toBeVisible();
    await expect(canvas.queryByRole("textbox")).toBeNull();
  },
};

export const DefaultPolicy: Story = {
  args: { route: "/policies/default/versions/3" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("heading", { level: 1, name: "default v3" })).toBeVisible();
    await expect(
      within(canvas.getByRole("region", { name: "Policy" })).getByText("Every 1 h, and 5 min after a commit"),
    ).toBeVisible();
    const snapshots = within(canvas.getByRole("region", { name: "Expire snapshots" }));
    await expect(snapshots.getByText("Keep at least 10 snapshots")).toBeVisible();
    await expect(snapshots.getByText("Expire snapshots older than 1 d")).toBeVisible();
    await expect(
      within(canvas.getByRole("region", { name: "Remove orphan files" })).getByText("Remove orphan files older than 3 d"),
    ).toBeVisible();
  },
};

export const OnlyRewriteDataFiles: Story = {
  args: { route: "/policies/scratch/versions/1" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("heading", { level: 1, name: "scratch v1" })).toBeVisible();
    for (const name of ["Rewrite manifests", "Expire snapshots", "Remove orphan files"]) {
      await expect(within(canvas.getByRole("region", { name })).getByText("Not in this policy")).toBeVisible();
    }
    await expect(
      within(canvas.getByRole("region", { name: "Rewrite data files" })).getByText("Reducible files at most 5, per partition"),
    ).toBeVisible();
    await expect(within(canvas.getByRole("region", { name: "Policy" })).getByText("On: nothing is started")).toBeVisible();
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
