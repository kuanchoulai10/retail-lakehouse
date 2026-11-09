import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import { useState } from "react";
import { IconBook, IconChevronDown, IconChevronRight } from "../../icons";
import { expectFocusRing, expectNoHorizontalPageScroll } from "../../stories/assertions";
import { List, ListItem } from "./List";

const onSelect = fn();

const meta = {
  title: "Components/List",
  component: List,
  parameters: {
    docs: {
      description: {
        component:
          "Expanded departs from Serendie: rows are 36px high at minimum (44px below 768px " +
          "and under a coarse pointer).",
      },
    },
  },
} satisfies Meta<typeof List>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <List aria-label="Recent runs">
      <ListItem title="Compaction" description="sales.orders" leadingIcon={<IconBook />} />
      <ListItem title="Snapshot expiry" description="sales.items" onSelect={onSelect} />
      <ListItem title="Selected row" isSelected onSelect={onSelect} />
    </List>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getAllByRole("listitem")).toHaveLength(3);
    const buttons = canvas.getAllByRole("button") as [HTMLElement, HTMLElement];
    await userEvent.tab();
    await expectFocusRing(buttons[0]);
    await userEvent.keyboard("{Enter}");
    await expect(onSelect).toHaveBeenCalledTimes(1);
    await expect(buttons[1]).toHaveAttribute("aria-current", "true");
  },
};

const onOpenRow = fn();

function DisclosureRow() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <ListItem
        title="4 runs found nothing to do"
        leadingIcon={open ? <IconChevronDown /> : <IconChevronRight />}
        aria-expanded={open}
        aria-controls={open ? "hidden-runs" : undefined}
        onSelect={() => setOpen((value) => !value)}
      />
      {open && <ListItem id="hidden-runs" title="Schedule at 09:42" />}
    </>
  );
}

// A row whose button opens it, with an action beside the button rather than inside it (a link
// cannot sit in a button), and a row that discloses more rows.
export const WithTrailingAction: Story = {
  render: () => (
    <List aria-label="Reconciliations">
      <ListItem
        title="Started Rewrite data files"
        description="Catalog commit at 10:42"
        onSelect={onOpenRow}
        trailingAction={<a href="#run-42">Open run</a>}
      />
      <DisclosureRow />
    </List>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const row = canvas.getByRole("button", { name: /Started Rewrite data files/ });
    const link = canvas.getByRole("link", { name: "Open run" });
    await expect(row).not.toContainElement(link);
    await expect(row.closest("li")).toContainElement(link);

    await userEvent.tab();
    await expectFocusRing(row);
    await userEvent.keyboard("{Enter}");
    await expect(onOpenRow).toHaveBeenCalledTimes(1);
    await userEvent.tab();
    await expect(link).toHaveFocus();

    const disclosure = canvas.getByRole("button", { name: "4 runs found nothing to do" });
    await userEvent.tab();
    await expectFocusRing(disclosure);
    await expect(disclosure).toHaveAttribute("aria-expanded", "false");
    await userEvent.keyboard(" ");
    await expect(disclosure).toHaveAttribute("aria-expanded", "true");
    await expect(disclosure).toHaveAttribute("aria-controls", "hidden-runs");
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
