import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import {
  expectFocusRing,
  expectNoHorizontalPageScroll,
  portalQueries,
} from "../../stories/assertions";
import { Breadcrumbs } from "../Breadcrumbs/Breadcrumbs";
import { Button } from "../Button/Button";
import { TitleBar } from "./TitleBar";

const onRetry = fn();
const onDelete = fn();
const onPause = fn();
const LONG_TITLE = "sales_orders_with_a_very_long_name_that_runs_to_sixty_characters";

const meta = {
  title: "Components/TitleBar",
  component: TitleBar,
  args: {
    title: "sales.orders",
    actions: <Button>Run now</Button>,
    overflowActions: [
      { label: "Run now", onSelect: onRetry },
      {
        label: "Pause",
        onSelect: onPause,
        disabled: true,
        description: "Only an active table can be paused",
      },
      { label: "Delete", onSelect: onDelete, destructive: true },
    ],
  },
  parameters: {
    docs: {
      description: {
        component:
          "Not in Serendie. Below 768px the actions collapse into an overflow menu when " +
          "overflowActions is given; an overflow action can be disabled and carry a description " +
          "(shown under its label, and its accessible description) saying why. A long title truncates " +
          "and carries the full text in a title.",
      },
    },
  },
} satisfies Meta<typeof TitleBar>;

export default meta;

type Story = StoryObj<typeof meta>;

const crumbs = (
  <Breadcrumbs
    items={[{ label: "Tables", href: "/tables" }, { label: "sales.orders" }]}
    renderLink={(item, children) => <a href={`#${item.href}`}>{children}</a>}
  />
);

export const Default: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  args: { breadcrumbs: crumbs },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("heading", { level: 1, name: "sales.orders" })).toBeVisible();
    await expect(canvas.getByRole("button", { name: "Run now" })).toBeVisible();
    await expect(canvasElement.querySelector("[aria-label='More actions']")).not.toBeVisible();
  },
};

export const PhoneOverflow: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  args: {
    breadcrumbs: crumbs,
    title: LONG_TITLE,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const heading = canvas.getByRole("heading", { level: 1, name: LONG_TITLE });
    await expect(heading).toHaveClass("truncate");
    await expect(heading).toHaveAttribute("title", LONG_TITLE);
    await expect(heading.scrollWidth).toBeGreaterThan(heading.clientWidth);
    await expect(canvas.queryByRole("button", { name: "Run now" })).toBeNull();
    const more = canvas.getByRole("button", { name: "More actions" });
    await userEvent.tab();
    await userEvent.tab();
    await expectFocusRing(more);
    await userEvent.keyboard("{Enter}");
    const portal = portalQueries(canvasElement);
    await userEvent.keyboard("{ArrowDown}");
    const pause = await portal.findByRole("menuitem", { name: "Pause" });
    await expect(pause).toHaveAttribute("aria-disabled", "true");
    await expect(pause).toHaveAccessibleName("Pause");
    await expect(pause).toHaveAccessibleDescription("Only an active table can be paused");
    await expect(portal.getByText("Only an active table can be paused")).toBeVisible();
    await userEvent.click(pause, { pointerEventsCheck: 0 });
    await expect(onPause).not.toHaveBeenCalled();
    await userEvent.click(await portal.findByRole("menuitem", { name: "Delete" }));
    await expect(onDelete).toHaveBeenCalledTimes(1);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const PhoneWithoutOverflow: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  args: { overflowActions: undefined },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("button", { name: "Run now" })).toBeVisible();
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
