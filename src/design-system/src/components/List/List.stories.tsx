import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import { IconBook } from "../../icons";
import { expectFocusRing } from "../../stories/assertions";
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
