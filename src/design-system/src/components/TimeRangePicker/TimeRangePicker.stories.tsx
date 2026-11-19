import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { expect, userEvent, within } from "storybook/test";
import { expectFocusRing, expectNoHorizontalPageScroll } from "../../stories/assertions";
import { TimeRangePicker } from "./TimeRangePicker";

const OPTIONS = [
  { value: "1h", label: "1h", description: "Last 1 hour" },
  { value: "3h", label: "3h", description: "Last 3 hours" },
  { value: "6h", label: "6h", description: "Last 6 hours" },
];

function Picker() {
  const [value, setValue] = useState("6h");
  return (
    <div className="flex flex-col gap-2">
      <TimeRangePicker options={OPTIONS} value={value} onValueChange={setValue} />
      <p className="type-body-small text-on-surface-variant" data-testid="chosen">
        {value}
      </p>
    </div>
  );
}

const meta = {
  title: "Charts/TimeRangePicker",
  component: TimeRangePicker,
  args: { options: OPTIONS, value: "6h", onValueChange: () => undefined },
  parameters: {
    docs: {
      description: {
        component:
          "No Serendie counterpart (a segmented control). Picks one of a few preset ranges; " +
          "one is always chosen. Arrow keys move between ranges, Enter or Space picks one. " +
          "Expanded departs from Serendie: options are 36px high (44px below 768px and under a " +
          "coarse pointer).",
      },
    },
  },
} satisfies Meta<typeof TimeRangePicker>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => <Picker />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const group = canvas.getByRole("radiogroup", { name: "Time range" });
    const [oneHour, threeHours, sixHours] = within(group).getAllByRole("radio") as [
      HTMLElement,
      HTMLElement,
      HTMLElement,
    ];
    await expect(sixHours).toHaveAttribute("aria-checked", "true");
    await expect(sixHours).toHaveAccessibleName("Last 6 hours");
    await userEvent.tab();
    await expectFocusRing(sixHours);
    await userEvent.keyboard("{ArrowLeft}");
    await expectFocusRing(threeHours);
    await userEvent.keyboard("{Enter}");
    await expect(threeHours).toHaveAttribute("aria-checked", "true");
    await expect(canvas.getByTestId("chosen")).toHaveTextContent("3h");
    await userEvent.keyboard("{ArrowLeft}");
    await expectFocusRing(oneHour);
    await userEvent.keyboard(" ");
    await expect(canvas.getByTestId("chosen")).toHaveTextContent("1h");
    await userEvent.keyboard(" ");
    await expect(oneHour).toHaveAttribute("aria-checked", "true");
    await expect(canvas.getByTestId("chosen")).toHaveTextContent("1h");
    await userEvent.tab();
    await expect(group).not.toContainElement(canvasElement.ownerDocument.activeElement as HTMLElement);
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  render: () => <Picker />,
  play: async ({ canvasElement }) => {
    const option = within(canvasElement).getAllByRole("radio")[0] as HTMLElement;
    await expect(option.getBoundingClientRect().height).toBeGreaterThanOrEqual(44);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
