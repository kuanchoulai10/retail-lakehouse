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
          "the same 36px / 44px controls as the rest of the system. " +
          "Pass `modal={false}` for a side panel next to a list.",
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

function SidePanelHarness({ startOpen = false }: { startOpen?: boolean }) {
  const [isOpen, setIsOpen] = useState(startOpen);
  const [otherPresses, setOtherPresses] = useState(0);
  return (
    <div className="flex items-center gap-2 p-4">
      <Button onClick={() => setIsOpen(true)}>Open</Button>
      <Button styleType="outlined" onClick={() => setOtherPresses((presses) => presses + 1)}>
        Other
      </Button>
      <output aria-label="Other presses">{otherPresses}</output>
      <Drawer title="Run details" isOpen={isOpen} onOpenChange={setIsOpen} modal={false}>
        <Button styleType="outlined">Retry run</Button>
      </Drawer>
    </div>
  );
}

export const SidePanel: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  render: () => <SidePanelHarness />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.tab();
    await expect(canvas.getByRole("button", { name: "Open" })).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    const heading = await portalQueries(canvasElement).findByRole("heading", { name: "Run details" });
    await waitFor(() => expect(heading).toHaveFocus());
    await userEvent.click(canvas.getByRole("button", { name: "Other" }));
    await expect(canvas.getByRole("status", { name: "Other presses" })).toHaveTextContent("1");
    await expect(portalQueries(canvasElement).getByRole("dialog")).toBeInTheDocument();
    await expect(document.body.querySelector(".bg-scrim")).toBeNull();
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(portalQueries(canvasElement).queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(canvas.getByRole("button", { name: "Open" })).toHaveFocus());
  },
};

function SidePanelSwitchHarness() {
  const [record, setRecord] = useState<string | null>(null);
  return (
    <div className="flex items-center gap-2 p-4">
      {["A", "B"].map((name) => (
        <Button key={name} onClick={() => setRecord(name)}>
          {`Row ${name}`}
        </Button>
      ))}
      <Drawer
        title={`Record ${record ?? ""}`}
        contentKey={record ?? undefined}
        isOpen={record !== null}
        onOpenChange={(isOpen) => {
          if (!isOpen) {
            setRecord(null);
          }
        }}
        modal={false}
      >
        Details of {record}
      </Drawer>
    </div>
  );
}

export const SidePanelSwitch: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  render: () => <SidePanelSwitchHarness />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.tab();
    await expect(canvas.getByRole("button", { name: "Row A" })).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    const first = await portalQueries(canvasElement).findByRole("heading", { name: "Record A" });
    await waitFor(() => expect(first).toHaveFocus());
    await userEvent.click(canvas.getByRole("button", { name: "Row B" }));
    const second = await portalQueries(canvasElement).findByRole("heading", { name: "Record B" });
    await waitFor(() => expect(second).toHaveFocus());
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(portalQueries(canvasElement).queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(canvas.getByRole("button", { name: "Row B" })).toHaveFocus());
  },
};

export const SidePanelPhone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  render: () => <SidePanelHarness startOpen />,
  play: async ({ canvasElement }) => {
    const dialog = await portalQueries(canvasElement).findByRole("dialog", { name: "Run details" });
    await expect(dialog.getBoundingClientRect().width).toBe(window.innerWidth);
    await expect(document.body.querySelector(".bg-scrim")).not.toBeNull();
    const controls = within(dialog).getAllByRole("button");
    controls.at(-1)?.focus();
    await userEvent.tab();
    await expect(controls[0]).toHaveFocus();
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
