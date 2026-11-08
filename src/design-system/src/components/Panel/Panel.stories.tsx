import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { expectNoHorizontalPageScroll } from "../../stories/assertions";
import { Button } from "../Button/Button";
import { Panel } from "./Panel";

const meta = {
  title: "Components/Panel",
  component: Panel,
  args: { title: "Maintenance", children: "Compaction runs nightly." },
  parameters: {
    docs: {
      description: {
        component:
          "No Serendie counterpart. A surface-container card with an outline border, the large " +
          "radius and no shadow. Sizes are the same in both window classes.",
      },
    },
  },
} satisfies Meta<typeof Panel>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("heading", { name: "Maintenance" })).toBeVisible();
    const panel = canvas.getByRole("region", { name: "Maintenance" });
    await expect(getComputedStyle(panel).boxShadow).toBe("none");
    await expect(getComputedStyle(panel).borderTopWidth).toBe("1px");
  },
};

export const WithActions: Story = {
  args: { actions: <Button size="small">Edit</Button> },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("button", { name: "Edit" })).toBeVisible();
  },
};

export const Untitled: Story = {
  args: { title: undefined },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  args: { actions: <Button size="small">Edit</Button> },
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
