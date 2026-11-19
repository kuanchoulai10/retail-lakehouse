import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, waitFor, within } from "storybook/test";
import { expectFocusRing, expectNoHorizontalPageScroll, portalQueries, resolvedColor } from "../../stories/assertions";
import { TooltipProvider } from "../Tooltip/Tooltip";
import { Tracker, type TrackerItem } from "./Tracker";

const STATUSES: TrackerItem["status"][] = ["positive", "positive", "notice", "positive", "negative", "positive", "neutral"];

const RUNS: TrackerItem[] = Array.from({ length: 24 }, (_, hour) => {
  const status = STATUSES[hour % STATUSES.length] as TrackerItem["status"];
  const outcome = { positive: "succeeded", notice: "partly succeeded", negative: "failed", neutral: "did not run" }[status];
  return { key: `h${hour}`, status, label: `${String(hour).padStart(2, "0")}:00 — maintenance ${outcome}` };
});

const meta = {
  title: "Charts/Tracker",
  component: Tracker,
  args: { label: "Maintenance runs in the last 24 hours", items: RUNS },
  parameters: {
    docs: {
      description: {
        component:
          "No Serendie counterpart. One block per period, coloured by its status. The blocks " +
          "are one tab stop: arrow keys, Home and End move between them, and the focused " +
          "block's tooltip says what happened. Sizes are the same in both window classes.",
      },
    },
  },
  decorators: [(Story) => <TooltipProvider delayDuration={0}>{Story()}</TooltipProvider>],
} satisfies Meta<typeof Tracker>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const group = within(canvasElement).getByRole("group", { name: "Maintenance runs in the last 24 hours" });
    const blocks = within(group).getAllByRole("img");
    await expect(blocks).toHaveLength(24);
    await expect(getComputedStyle(blocks[0] as HTMLElement).backgroundColor).toBe(
      resolvedColor("positive-text", canvasElement),
    );
    await expect(getComputedStyle(blocks[4] as HTMLElement).backgroundColor).toBe(
      resolvedColor("negative-text", canvasElement),
    );
    await userEvent.tab();
    await expectFocusRing(blocks[0] as HTMLElement);
    await waitFor(() =>
      expect(portalQueries(canvasElement).getByRole("tooltip")).toHaveTextContent("00:00 — maintenance succeeded"),
    );
    await userEvent.keyboard("{ArrowRight}");
    await expectFocusRing(blocks[1] as HTMLElement);
    await userEvent.keyboard("{End}");
    await expectFocusRing(blocks[23] as HTMLElement);
    await waitFor(() => expect(portalQueries(canvasElement).getByRole("tooltip")).toHaveTextContent("23:00"));
    await userEvent.keyboard("{ArrowRight}");
    await expectFocusRing(blocks[23] as HTMLElement);
    await userEvent.keyboard("{Home}");
    await expectFocusRing(blocks[0] as HTMLElement);
    await userEvent.keyboard("{ArrowLeft}");
    await expectFocusRing(blocks[0] as HTMLElement);
    await userEvent.keyboard("{ArrowRight}{ArrowRight}");
    await userEvent.tab({ shift: true });
    await userEvent.tab();
    await expectFocusRing(blocks[2] as HTMLElement);
  },
};

export const Empty: Story = {
  args: { items: [] },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("No data in this time range")).toBeVisible();
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  args: { items: [...RUNS, ...RUNS.map((run) => ({ ...run, key: `${run.key}-b` }))] },
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
