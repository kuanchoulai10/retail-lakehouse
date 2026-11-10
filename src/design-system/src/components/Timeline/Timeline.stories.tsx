import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import { useState } from "react";
import { IconChevronDown, IconChevronRight } from "../../icons";
import { expectFocusRing, expectNoHorizontalPageScroll } from "../../stories/assertions";
import { Timeline, TimelineItem } from "./Timeline";

const onOpenEntry = fn();
const onOpenNested = fn();

const meta = {
  title: "Components/Timeline",
  component: Timeline,
  parameters: {
    docs: {
      description: {
        component:
          "An open history of events, newest first: a thin line down the left joins one marker per " +
          "entry, with no box and no row borders. `filled` (theme colour) marks an entry that started " +
          "something, `outlined` any other entry, and `dashed` a folded stretch of quiet entries, drawn " +
          "in lighter, smaller text. Each entry's content is a button; an action such as a link sits " +
          "beside it, outside the button. Serendie has no timeline; the name is plain. Expanded " +
          "departs from Serendie: entries are 36px high at minimum (44px below 768px and under a " +
          "coarse pointer).",
      },
    },
  },
} satisfies Meta<typeof Timeline>;

export default meta;

type Story = StoryObj<typeof meta>;

function FoldedEntry() {
  const [open, setOpen] = useState(false);
  return (
    <TimelineItem
      marker="dashed"
      title={
        <span className="flex items-center gap-1">
          {open ? <IconChevronDown aria-hidden="true" size={16} /> : <IconChevronRight aria-hidden="true" size={16} />}
          4 checks found nothing to do, 06:42–09:42
        </span>
      }
      aria-expanded={open}
      aria-controls={open ? "folded-entries" : undefined}
      onSelect={() => setOpen((value) => !value)}
    >
      {open && (
        <Timeline id="folded-entries" nested>
          <TimelineItem title="Schedule at 09:42" onSelect={onOpenNested} />
          <TimelineItem title="Schedule at 08:42" onSelect={onOpenNested} />
        </Timeline>
      )}
    </TimelineItem>
  );
}

function History() {
  return (
    <Timeline aria-label="Maintenance checks">
      <TimelineItem
        marker="filled"
        title="Started Rewrite data files"
        description="Catalog commit at 10:42, 12 min ago"
        onSelect={onOpenEntry}
        trailingAction={<a href="#run-42">Run 0b9e3c1a</a>}
      />
      <FoldedEntry />
      <TimelineItem marker="outlined" title="Nothing to do" description="Schedule at 05:42, 5 h ago" onSelect={onOpenEntry} />
    </Timeline>
  );
}

export const Default: Story = {
  render: () => <History />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const timeline = canvas.getByRole("list", { name: "Maintenance checks" });
    await expect(within(timeline).getAllByRole("listitem")).toHaveLength(3);
    await expect(getComputedStyle(timeline).borderTopWidth).toBe("0px");
    const markers = Array.from(timeline.querySelectorAll("[data-marker]")).map((m) => m.getAttribute("data-marker"));
    await expect(markers).toEqual(["filled", "dashed", "outlined"]);

    const entry = canvas.getByRole("button", { name: /Started Rewrite data files/ });
    const link = canvas.getByRole("link", { name: "Run 0b9e3c1a" });
    await expect(entry).not.toContainElement(link);
    await expect(entry.closest("li")).toContainElement(link);

    await userEvent.tab();
    await expectFocusRing(entry);
    await userEvent.keyboard("{Enter}");
    await expect(onOpenEntry).toHaveBeenCalledTimes(1);
    await userEvent.tab();
    await expect(link).toHaveFocus();

    const fold = canvas.getByRole("button", { name: /4 checks found nothing to do/ });
    await userEvent.tab();
    await expectFocusRing(fold);
    await expect(fold).toHaveAttribute("aria-expanded", "false");
    await userEvent.keyboard(" ");
    await expect(fold).toHaveAttribute("aria-expanded", "true");
    await expect(fold).toHaveAttribute("aria-controls", "folded-entries");

    const nested = canvasElement.ownerDocument.getElementById("folded-entries") as HTMLElement;
    await expect(fold.closest("li")).toContainElement(nested);
    await expect(nested.querySelectorAll("[data-marker]")).toHaveLength(0);
    await userEvent.tab();
    await expectFocusRing(canvas.getByRole("button", { name: "Schedule at 09:42" }));
    await userEvent.keyboard("{Enter}");
    await expect(onOpenNested).toHaveBeenCalledTimes(1);

    await userEvent.keyboard(" ");
    await expect(onOpenNested).toHaveBeenCalledTimes(2);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  render: () => (
    <Timeline aria-label="Maintenance checks">
      <TimelineItem
        marker="filled"
        title="Started Rewrite data files, Rewrite manifests, Expire snapshots, Remove orphan files"
        description="Catalog commit × 3 at 10:42, 12 min ago"
        onSelect={onOpenEntry}
        trailingAction={<a href="#run-42">Run 0b9e3c1a</a>}
      />
      <TimelineItem marker="outlined" title="Skipped: table paused" description="Schedule at 05:42" />
    </Timeline>
  ),
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("link", { name: "Run 0b9e3c1a" })).toBeVisible();
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
