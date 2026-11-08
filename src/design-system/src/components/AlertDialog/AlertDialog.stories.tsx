import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { expect, fn, userEvent, waitFor } from "storybook/test";
import { exerciseOverlay, portalQueries } from "../../stories/assertions";
import { Button } from "../Button/Button";
import { AlertDialog, AlertDialogAction, AlertDialogCancel } from "./AlertDialog";

const meta = {
  title: "Components/AlertDialog",
  component: AlertDialog,
  args: {
    isOpen: false,
    onOpenChange: fn(),
    title: "Delete preset",
    children: null,
  },
  parameters: {
    docs: {
      description: {
        component:
          "No Serendie counterpart. Centred at every width with 36px controls on desktop and " +
          "44px below 768px; it has no close button and does not dismiss on outside click.",
      },
    },
  },
} satisfies Meta<typeof AlertDialog>;

export default meta;

type Story = StoryObj<typeof meta>;

function Harness({ onConfirm }: { onConfirm: () => void }) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div className="p-4">
      <Button styleType="outlined" onClick={() => setIsOpen(true)}>
        Delete preset
      </Button>
      <AlertDialog
        title="Delete this preset?"
        description="Tables using it fall back to the default preset."
        isOpen={isOpen}
        onOpenChange={setIsOpen}
        footer={
          <>
            <AlertDialogCancel styleType="ghost">Keep</AlertDialogCancel>
            <AlertDialogAction onClick={onConfirm}>Delete</AlertDialogAction>
          </>
        }
      >
        This cannot be undone.
      </AlertDialog>
    </div>
  );
}

export const Default: Story = {
  render: () => <Harness onConfirm={fn()} />,
  play: async ({ canvasElement }) => {
    await exerciseOverlay(canvasElement, "Delete preset", "alertdialog");
  },
};

export const ConfirmAndCancel: Story = {
  render: () => <Harness onConfirm={fn()} />,
  play: async ({ canvasElement }) => {
    const portal = portalQueries(canvasElement);
    await userEvent.tab();
    await userEvent.keyboard("{Enter}");
    const keep = await portal.findByRole("button", { name: "Keep" });
    await waitFor(() => expect(keep).toHaveFocus());
    await userEvent.tab();
    await expect(portal.getByRole("button", { name: "Delete" })).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await waitFor(() => expect(portal.queryByRole("alertdialog")).toBeNull());
  },
};
