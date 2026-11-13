import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { getListCompactionRoundsMockHandler } from "@/api/generated/compaction-rounds/compaction-rounds.msw";
import { apiError } from "@/stories/apiError";
import { ConsolePage } from "@/stories/ConsolePage";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";

const meta = {
  title: "Pages/Compaction rounds",
  component: ConsolePage,
  args: { route: "/compaction-rounds" },
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof ConsolePage>;

export default meta;
type Story = StoryObj<typeof meta>;

async function openNewestRound(canvasElement: HTMLElement) {
  const canvas = within(canvasElement);
  await userEvent.click(await canvas.findByRole("button", { name: "Expand round 2026-11-13T02:00:00Z" }));
}

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("0.47 of 0.50 (94%)")).toBeVisible();
    await expect(canvas.getByRole("link", { name: "Compaction rounds" })).toHaveAttribute("aria-current", "page");
  },
};

export const Expanded: Story = {
  play: async ({ canvasElement }) => {
    await openNewestRound(canvasElement);
    const canvas = within(canvasElement);
    const picks = within(canvas.getByRole("table", { name: "Partitions round 2026-11-13T02:00:00Z granted" }));
    await expect(picks.getByRole("link", { name: "iceberg.retail.orders" })).toBeVisible();
    await expect(picks.getByText("2.96")).toBeVisible();
    const skips = within(canvas.getByRole("table", { name: "Partitions round 2026-11-13T02:00:00Z skipped" }));
    await expect(skips.getByText("Budget used")).toBeVisible();
    await expect(skips.getByText("Overdue", { selector: "span" })).toBeVisible();
    await expect(canvas.getByText("The first 1 of 4 skipped partitions, in rank order.")).toBeVisible();
  },
};

export const Empty: Story = {
  beforeEach({ msw }) {
    msw.use(getListCompactionRoundsMockHandler([]));
  },
  play: async ({ canvasElement }) => {
    await expect(await within(canvasElement).findByText("No compaction round has run yet.")).toBeVisible();
  },
};

export const LoadError: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("get", "/v1/compaction-rounds", "database down", 500));
  },
  play: async ({ canvasElement }) => {
    await expect(
      await within(canvasElement).findByText("Could not load compaction rounds: database down"),
    ).toBeVisible();
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await openNewestRound(canvasElement);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
