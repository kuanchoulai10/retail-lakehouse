import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { expect, fn, userEvent, waitFor, within } from "storybook/test";
import {
  expectFocusRing,
  expectNoHorizontalPageScroll,
  portalQueries,
} from "../../stories/assertions";
import {
  DatePicker,
  type DateRange,
  type RangeDatePickerProps,
  type SingleDatePickerProps,
} from "./DatePicker";

const NOV = (day: number) => new Date(2026, 10, day);

// Holds the value the way a page would, so a story can watch the field change.
function RangeHarness(props: Omit<RangeDatePickerProps, "selectionMode">) {
  const [value, setValue] = useState<DateRange | undefined>(props.value);
  return (
    <DatePicker
      {...props}
      selectionMode="range"
      value={value}
      onValueChange={(next) => {
        setValue(next);
        props.onValueChange?.(next);
      }}
    />
  );
}

function SingleHarness(props: Omit<SingleDatePickerProps, "selectionMode">) {
  const [value, setValue] = useState<Date | undefined>(props.value);
  return (
    <DatePicker
      {...props}
      value={value}
      onValueChange={(next) => {
        setValue(next);
        props.onValueChange?.(next);
      }}
    />
  );
}

const meta = {
  title: "Components/DatePicker",
  component: DatePicker,
  args: { label: "Committed between", selectionMode: "range", onValueChange: fn() },
  decorators: [
    (Story) => (
      <div className="h-120 max-w-sm p-4">
        <Story />
      </div>
    ),
  ],
  parameters: {
    docs: {
      description: {
        component:
          "Serendie's DatePicker: a field with a calendar icon that opens a calendar, in single " +
          "or range selection. Departs from Serendie: the field is one button showing the chosen " +
          "dates (Serendie types them into inputs), the month caption has no year select, and a " +
          "range is picked as two clicks, start then end. Expanded is 36px high (Serendie 48px) " +
          "and stays 44px below 768px and under a coarse pointer.",
      },
    },
  },
} satisfies Meta<RangeDatePickerProps>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Range: Story = {
  render: (args) => (
    <RangeHarness
      label={args.label}
      value={{ from: NOV(3), to: NOV(5) }}
      onValueChange={args.onValueChange as (value: DateRange | undefined) => void}
    />
  ),
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    const portal = portalQueries(canvasElement);
    const trigger = canvas.getByRole("button", { name: "Committed between" });
    await expect(trigger).toHaveAccessibleDescription("Nov 3, 2026 – Nov 5, 2026");

    await userEvent.tab();
    await expectFocusRing(trigger);
    await userEvent.keyboard("{Enter}");
    const calendar = await portal.findByRole("dialog", { name: "Choose dates" });
    await expect(within(calendar).getByText("November 2026")).toBeVisible();
    await waitFor(() => expect(document.activeElement).toHaveAccessibleName(/November 3(rd)?, 2026/));

    await userEvent.keyboard("{ArrowRight}{Enter}");
    await expect(portal.getByRole("dialog")).toBeVisible();
    await userEvent.keyboard("{ArrowRight}{ArrowRight}{Enter}");

    await expect(args.onValueChange).toHaveBeenLastCalledWith({ from: NOV(4), to: NOV(6) });
    await waitFor(() => expect(portal.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(trigger).toHaveFocus());
    await expect(trigger).toHaveAccessibleDescription("Nov 4, 2026 – Nov 6, 2026");
  },
};

export const RangeEndBeforeStart: Story = {
  render: (args) => (
    <RangeHarness
      label={args.label}
      value={{ from: NOV(10), to: NOV(12) }}
      onValueChange={args.onValueChange as (value: DateRange | undefined) => void}
    />
  ),
  play: async ({ canvasElement, args }) => {
    const portal = portalQueries(canvasElement);
    await userEvent.click(within(canvasElement).getByRole("button", { name: "Committed between" }));
    await userEvent.click(await portal.findByRole("button", { name: /November 10(th)?, 2026/ }));
    await userEvent.click(portal.getByRole("button", { name: /November 7(th)?, 2026/ }));
    await expect(args.onValueChange).toHaveBeenLastCalledWith({ from: NOV(7), to: NOV(10) });
  },
};

export const EscapeKeepsTheValue: Story = {
  render: (args) => (
    <RangeHarness
      label={args.label}
      value={{ from: NOV(3), to: NOV(5) }}
      onValueChange={args.onValueChange as (value: DateRange | undefined) => void}
    />
  ),
  play: async ({ canvasElement, args }) => {
    const portal = portalQueries(canvasElement);
    const trigger = within(canvasElement).getByRole("button", { name: "Committed between" });
    await userEvent.click(trigger);
    await portal.findByRole("dialog");
    await waitFor(() => expect(document.activeElement).toHaveAccessibleName(/November 3(rd)?, 2026/));
    await userEvent.keyboard("{ArrowRight}{Enter}{Escape}");
    await waitFor(() => expect(portal.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(trigger).toHaveFocus());
    await expect(args.onValueChange).not.toHaveBeenCalled();
    await expect(trigger).toHaveAccessibleDescription("Nov 3, 2026 – Nov 5, 2026");
  },
};

export const Clear: Story = {
  render: (args) => (
    <RangeHarness
      label={args.label}
      value={{ from: NOV(3), to: NOV(5) }}
      onValueChange={args.onValueChange as (value: DateRange | undefined) => void}
    />
  ),
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    const clear = canvas.getByRole("button", { name: "Clear dates" });
    await userEvent.tab();
    await userEvent.tab();
    await expectFocusRing(clear);
    await userEvent.keyboard("{Enter}");
    await expect(args.onValueChange).toHaveBeenLastCalledWith(undefined);
    const trigger = canvas.getByRole("button", { name: "Committed between" });
    await expect(trigger).toHaveTextContent("Start date");
    await expect(trigger).toHaveTextContent("End date");
    await expect(canvas.queryByRole("button", { name: "Clear dates" })).toBeNull();
    await waitFor(() => expect(trigger).toHaveFocus());
  },
};

export const Empty: Story = {
  args: { startPlaceholder: "Since", endPlaceholder: "Until" },
  play: async ({ canvasElement }) => {
    const trigger = within(canvasElement).getByRole("button", { name: "Committed between" });
    await expect(trigger).toHaveTextContent("Since");
    await expect(trigger).toHaveTextContent("Until");
    await expect(within(canvasElement).queryByRole("button", { name: "Clear dates" })).toBeNull();
  },
};

export const Single: Story = {
  render: (args) => (
    <SingleHarness
      label="Run after"
      value={NOV(3)}
      onValueChange={args.onValueChange as (value: Date | undefined) => void}
    />
  ),
  play: async ({ canvasElement, args }) => {
    const portal = portalQueries(canvasElement);
    const trigger = within(canvasElement).getByRole("button", { name: "Run after" });
    await expect(trigger).toHaveAccessibleDescription("Nov 3, 2026");
    await userEvent.click(trigger);
    await portal.findByRole("dialog", { name: "Choose a date" });
    await waitFor(() => expect(document.activeElement).toHaveAccessibleName(/November 3(rd)?, 2026/));
    await userEvent.keyboard("{ArrowDown}{Enter}");
    await expect(args.onValueChange).toHaveBeenLastCalledWith(NOV(10));
    await waitFor(() => expect(portal.queryByRole("dialog")).toBeNull());
    await expect(trigger).toHaveAccessibleDescription("Nov 10, 2026");
  },
};

export const LatestDate: Story = {
  args: { value: { from: NOV(3), to: NOV(5) }, maxDate: NOV(9) },
  play: async ({ canvasElement }) => {
    const portal = portalQueries(canvasElement);
    await userEvent.click(within(canvasElement).getByRole("button", { name: "Committed between" }));
    await expect(await portal.findByRole("button", { name: /November 10(th)?, 2026/ })).toBeDisabled();
    await expect(portal.getByRole("button", { name: /November 9(th)?, 2026/ })).toBeEnabled();
    await expect(portal.getByRole("button", { name: "Next month" })).toHaveAttribute("aria-disabled", "true");
    await userEvent.keyboard("{Escape}");
  },
};

export const Invalid: Story = {
  args: { invalid: true, invalidMessage: "End the range before today", description: "Commit time" },
  play: async ({ canvasElement }) => {
    const trigger = within(canvasElement).getByRole("button", { name: "Committed between" });
    await expect(trigger).toHaveAttribute("aria-invalid", "true");
    await expect(trigger).toHaveAccessibleDescription("Commit time End the range before today");
  },
};

export const Disabled: Story = {
  args: { disabled: true, value: { from: NOV(3), to: NOV(5) } },
  play: async ({ canvasElement }) => {
    const trigger = within(canvasElement).getByRole("button", { name: "Committed between" });
    await expect(trigger).toBeDisabled();
    await expect(within(canvasElement).queryByRole("button", { name: "Clear dates" })).toBeNull();
    await userEvent.tab();
    await expect(trigger).not.toHaveFocus();
  },
};

export const Touch: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  args: { value: { from: NOV(3), to: NOV(5) } },
  play: async ({ canvasElement }) => {
    const trigger = within(canvasElement).getByRole("button", { name: "Committed between" });
    await expect(trigger.getBoundingClientRect().height).toBe(44);
    await userEvent.click(trigger);
    const day = await portalQueries(canvasElement).findByRole("button", { name: /November 4(th)?, 2026/ });
    await expect(day.getBoundingClientRect().height).toBe(44);
    await expectNoHorizontalPageScroll(canvasElement);
    await userEvent.keyboard("{Escape}");
  },
};

export const Desktop: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  args: { value: { from: NOV(3), to: NOV(5) } },
  play: async ({ canvasElement }) => {
    const trigger = within(canvasElement).getByRole("button", { name: "Committed between" });
    await expect(trigger.getBoundingClientRect().height).toBe(36);
    await userEvent.click(trigger);
    const day = await portalQueries(canvasElement).findByRole("button", { name: /November 4(th)?, 2026/ });
    await expect(day.getBoundingClientRect().height).toBe(36);
    await userEvent.keyboard("{Escape}");
  },
};
