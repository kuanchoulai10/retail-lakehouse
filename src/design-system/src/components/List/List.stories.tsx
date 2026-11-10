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

// A list item has no action beside its row; a Timeline entry does.
// @ts-expect-error trailingAction is not a ListItem prop.
const rowWithAction = <ListItem title="x" trailingAction={<a href="#run-42">Open run</a>} />;
void rowWithAction;

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

// A row that discloses more rows.
export const Disclosure: Story = {
  render: () => (
    <List aria-label="Runs">
      <DisclosureRow />
    </List>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const disclosure = canvas.getByRole("button", { name: "4 runs found nothing to do" });
    await userEvent.tab();
    await expectFocusRing(disclosure);
    await expect(disclosure).toHaveAttribute("aria-expanded", "false");
    await userEvent.keyboard(" ");
    await expect(disclosure).toHaveAttribute("aria-expanded", "true");
    await expect(disclosure).toHaveAttribute("aria-controls", "hidden-runs");
    await userEvent.keyboard("{Enter}");
    await expect(disclosure).toHaveAttribute("aria-expanded", "false");
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
