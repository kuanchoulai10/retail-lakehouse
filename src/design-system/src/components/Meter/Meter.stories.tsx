import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { expectNoHorizontalPageScroll, resolvedColor } from "../../stories/assertions";
import { Meter } from "./Meter";

const meta = {
  title: "Charts/Meter",
  component: Meter,
  args: { label: "Files at target size", value: 72, valueText: "72%" },
  parameters: {
    docs: {
      description: {
        component:
          "No Serendie counterpart. A value within a known range, as a bar or a ring. It is " +
          "not a loading indicator. `tone` gives the fill a status colour when the value " +
          "itself is a status; otherwise it takes the theme colour. Sizes are the same in " +
          "both window classes.",
      },
    },
  },
  decorators: [(Story) => <div className="max-w-80">{Story()}</div>],
} satisfies Meta<typeof Meter>;

export default meta;

type Story = StoryObj<typeof meta>;

function fill(canvasElement: HTMLElement): HTMLElement {
  return canvasElement.querySelector("[data-meter-fill]") as HTMLElement;
}

export const Bar: Story = {
  play: async ({ canvasElement }) => {
    const meter = within(canvasElement).getByRole("meter", { name: "Files at target size" });
    await expect(meter).toHaveAttribute("aria-valuenow", "72");
    await expect(meter).toHaveAttribute("aria-valuemin", "0");
    await expect(meter).toHaveAttribute("aria-valuemax", "100");
    await expect(meter).toHaveAttribute("aria-valuetext", "72%");
    await expect(fill(canvasElement).style.width).toBe("72%");
    await expect(getComputedStyle(fill(canvasElement)).backgroundColor).toBe(resolvedColor("primary", canvasElement));
  },
};

export const OverMax: Story = {
  args: { label: "Snapshots kept", value: 140, max: 100, valueText: "140 of 100" },
  play: async ({ canvasElement }) => {
    await expect(fill(canvasElement).style.width).toBe("100%");
  },
};

export const Negative: Story = {
  args: { label: "Retention budget used", value: 96, valueText: "96%", tone: "negative" },
  play: async ({ canvasElement }) => {
    await expect(getComputedStyle(fill(canvasElement)).backgroundColor).toBe(
      resolvedColor("negative-text", canvasElement),
    );
  },
};

export const Ring: Story = {
  args: { variant: "ring" },
  play: async ({ canvasElement }) => {
    const meter = within(canvasElement).getByRole("meter", { name: "Files at target size" });
    await expect(within(meter).getByText("72%")).toBeVisible();
    await expect(fill(canvasElement).getAttribute("stroke-dasharray")).toBe("72 100");
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
