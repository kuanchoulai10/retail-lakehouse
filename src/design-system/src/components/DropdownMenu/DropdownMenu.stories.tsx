import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { expect, fn, userEvent, waitFor, within } from "storybook/test";
import { expectFocusRing, portalQueries } from "../../stories/assertions";
import { AlertDialog, AlertDialogAction, AlertDialogCancel } from "../AlertDialog/AlertDialog";
import { Button } from "../Button/Button";
import { ModalDialog } from "../ModalDialog/ModalDialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./DropdownMenu";

const meta = {
  title: "Components/DropdownMenu",
  component: DropdownMenu,
  parameters: {
    docs: {
      description: {
        component:
          "Expanded departs from Serendie: items are 36px high (Serendie 48px) and stay 44px " +
          "below 768px and under a coarse pointer.",
      },
    },
  },
} satisfies Meta<typeof DropdownMenu>;

export default meta;

type Story = StoryObj<typeof meta>;

const onRun = fn();
const onPriorityChange = fn();

export const Default: Story = {
  render: () => (
    <div className="h-64 p-4">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button styleType="outlined">Actions</Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem onSelect={onRun}>Run now</DropdownMenuItem>
          <DropdownMenuItem>Pause</DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuRadioGroup value="low" onValueChange={onPriorityChange}>
            <DropdownMenuRadioItem value="low">Low priority</DropdownMenuRadioItem>
            <DropdownMenuRadioItem value="high">High priority</DropdownMenuRadioItem>
          </DropdownMenuRadioGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  ),
  play: async ({ canvasElement }) => {
    const portal = portalQueries(canvasElement);
    const trigger = within(canvasElement).getByRole("button", { name: "Actions" });
    await userEvent.tab();
    await expectFocusRing(trigger);
    await userEvent.keyboard("{Enter}");
    const first = await portal.findByRole("menuitem", { name: "Run now" });
    await waitFor(() => expect(first).toHaveFocus());
    await userEvent.keyboard("{ArrowDown}");
    await expect(portal.getByRole("menuitem", { name: "Pause" })).toHaveFocus();
    await userEvent.keyboard("{ArrowUp}");
    await expect(first).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await expect(onRun).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(portal.queryByRole("menu")).toBeNull());
    await waitFor(() => expect(trigger).toHaveFocus());

    await userEvent.keyboard("{Enter}");
    await portal.findByRole("menu");
    await userEvent.keyboard("{ArrowDown}{ArrowDown}{ArrowDown}");
    const high = portal.getByRole("menuitemradio", { name: "High priority" });
    await expect(high).toHaveFocus();
    await expect(portal.getByRole("menuitemradio", { name: "Low priority" })).toBeChecked();
    await userEvent.keyboard("{Enter}");
    await expect(onPriorityChange).toHaveBeenCalledWith("high");
    await waitFor(() => expect(trigger).toHaveFocus());

    await userEvent.keyboard("{Enter}");
    await portal.findByRole("menu");
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(portal.queryByRole("menu")).toBeNull());
    await waitFor(() => expect(trigger).toHaveFocus());
  },
};

export const Touch: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  render: Default.render,
  play: async ({ canvasElement }) => {
    await userEvent.click(within(canvasElement).getByRole("button", { name: "Actions" }));
    const item = await portalQueries(canvasElement).findByRole("menuitem", { name: "Run now" });
    await expect(item.getBoundingClientRect().height).toBe(44);
    await userEvent.keyboard("{Escape}");
  },
};

export const Desktop: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  render: Default.render,
  play: async ({ canvasElement }) => {
    await userEvent.click(within(canvasElement).getByRole("button", { name: "Actions" }));
    const item = await portalQueries(canvasElement).findByRole("menuitem", { name: "Run now" });
    await expect(item.getBoundingClientRect().height).toBe(36);
    await userEvent.keyboard("{Escape}");
  },
};

function MenuToDialogHarness() {
  const [dialog, setDialog] = useState<"none" | "modal" | "alert">("none");
  const close = (isOpen: boolean) => {
    if (!isOpen) setDialog("none");
  };
  return (
    <div className="h-64 p-4">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button styleType="outlined">Actions</Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem onSelect={() => setDialog("modal")}>Rename</DropdownMenuItem>
          <DropdownMenuItem onSelect={() => setDialog("alert")}>Delete</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <ModalDialog title="Rename table" isOpen={dialog === "modal"} onOpenChange={close}>
        Rename sales.orders
      </ModalDialog>
      <AlertDialog
        title="Delete table"
        isOpen={dialog === "alert"}
        onOpenChange={close}
        footer={
          <>
            <AlertDialogCancel styleType="ghost">Keep</AlertDialogCancel>
            <AlertDialogAction>Delete</AlertDialogAction>
          </>
        }
      >
        Delete sales.orders
      </AlertDialog>
    </div>
  );
}

async function openFromMenu(canvasElement: HTMLElement, item: string, role: "dialog" | "alertdialog") {
  const portal = portalQueries(canvasElement);
  const trigger = within(canvasElement).getByRole("button", { name: "Actions" });
  await userEvent.keyboard("{Enter}");
  await waitFor(() => expect(portal.getByRole("menuitem", { name: "Rename" })).toHaveFocus());
  if (item === "Delete") await userEvent.keyboard("{ArrowDown}");
  await expect(portal.getByRole("menuitem", { name: item })).toHaveFocus();
  await userEvent.keyboard("{Enter}");
  const overlay = await portal.findByRole(role);
  await waitFor(() => expect(overlay).toContainElement(document.activeElement as HTMLElement));
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(portal.queryByRole(role)).toBeNull());
  await waitFor(() => expect(trigger).toHaveFocus());
}

export const ItemOpensModalDialog: Story = {
  render: () => <MenuToDialogHarness />,
  play: async ({ canvasElement }) => {
    await userEvent.tab();
    await expectFocusRing(within(canvasElement).getByRole("button", { name: "Actions" }));
    await openFromMenu(canvasElement, "Rename", "dialog");
  },
};

export const ItemOpensAlertDialog: Story = {
  render: () => <MenuToDialogHarness />,
  play: async ({ canvasElement }) => {
    await userEvent.tab();
    await expectFocusRing(within(canvasElement).getByRole("button", { name: "Actions" }));
    await openFromMenu(canvasElement, "Delete", "alertdialog");
  },
};
