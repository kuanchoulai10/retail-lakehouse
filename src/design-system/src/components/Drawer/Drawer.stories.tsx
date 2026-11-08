import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { expect, fn, userEvent, waitFor, within } from "storybook/test";
import {
  exerciseOverlay,
  expectNoHorizontalPageScroll,
  portalQueries,
} from "../../stories/assertions";
import { Button } from "../Button/Button";
import { Drawer } from "./Drawer";

const meta = {
  title: "Components/Drawer",
  component: Drawer,
  args: { isOpen: false, onOpenChange: fn(), title: "Run details", children: "Run 42" },
  parameters: {
    docs: {
      description: {
        component:
          "Expanded departs from Serendie: a 384px side panel (full width below 768px) with " +
          "the same 36px / 44px controls as the rest of the system.",
      },
    },
  },
} satisfies Meta<typeof Drawer>;

export default meta;

type Story = StoryObj<typeof meta>;

function Harness(props: Partial<React.ComponentProps<typeof Drawer>>) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div className="p-4">
      <Button onClick={() => setIsOpen(true)}>Open drawer</Button>
      <Drawer title="Run details" isOpen={isOpen} onOpenChange={setIsOpen} {...props}>
        <Button styleType="outlined">Retry run</Button>
      </Drawer>
    </div>
  );
}

export const Right: Story = {
  render: () => <Harness />,
  play: async ({ canvasElement }) => {
    await exerciseOverlay(canvasElement, "Open drawer", "dialog");
  },
};

export const Left: Story = {
  render: () => <Harness side="left" />,
  play: async ({ canvasElement }) => {
    await exerciseOverlay(canvasElement, "Open drawer", "dialog");
  },
};

export const HiddenTitle: Story = {
  render: () => <Harness hideTitle />,
  play: async ({ canvasElement }) => {
    await exerciseOverlay(canvasElement, "Open drawer", "dialog");
  },
};

export const RightEdge: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  args: { isOpen: true },
  play: async ({ canvasElement }) => {
    const dialog = await portalQueries(canvasElement).findByRole("dialog", { name: "Run details" });
    const rect = dialog.getBoundingClientRect();
    await expect(rect.right).toBe(window.innerWidth);
    await expect(rect.height).toBe(window.innerHeight);
    await expect(rect.width).toBeLessThanOrEqual(384);
  },
};

export const LeftEdge: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  args: { isOpen: true, side: "left" },
  play: async ({ canvasElement }) => {
    const dialog = await portalQueries(canvasElement).findByRole("dialog", { name: "Run details" });
    await expect(dialog.getBoundingClientRect().left).toBe(0);
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  args: { isOpen: true },
  play: async ({ canvasElement }) => {
    const dialog = await portalQueries(canvasElement).findByRole("dialog");
    await expect(dialog.getBoundingClientRect().width).toBeLessThanOrEqual(window.innerWidth);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

function PointerHarness() {
  const [isOpen, setIsOpen] = useState(false);
  return (
      <div className="p-4">
        <Button
          onClick={(event) => {
            event.currentTarget.blur();
            setIsOpen(true);
          }}
        >
          Open drawer
        </Button>
        <Drawer title="Run details" isOpen={isOpen} onOpenChange={setIsOpen}>
          Run 42
        </Drawer>
      </div>
  );
}

export const PointerOpened: Story = {
  render: () => <PointerHarness />,
  play: async ({ canvasElement }) => {
    const trigger = within(canvasElement).getByRole("button", { name: "Open drawer" });
    await userEvent.click(trigger);
    await portalQueries(canvasElement).findByRole("dialog");
    await expect(document.activeElement).not.toBe(document.body);
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(portalQueries(canvasElement).queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(trigger).toHaveFocus());
  },
};
