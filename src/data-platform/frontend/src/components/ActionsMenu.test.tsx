import { ModalDialog } from "@retail-lakehouse/design-system";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { ActionsMenu } from "./ActionsMenu";

// Mounts the dialog only once it is first opened, as TableHeader does with RunMaintenanceDialog.
function MenuWithDialog() {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <>
      <ActionsMenu items={[{ label: "Rename", onSelect: () => setIsOpen(true) }]} />
      {isOpen && (
        <ModalDialog title="Rename table" isOpen={isOpen} onOpenChange={setIsOpen}>
          Rename sales.orders
        </ModalDialog>
      )}
    </>
  );
}

describe("ActionsMenu", () => {
  it("runs the selected item", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    render(<ActionsMenu items={[{ label: "Delete", onSelect: onDelete }]} />);
    await user.click(screen.getByRole("button", { name: "Actions" }));
    await user.click(screen.getByRole("menuitem", { name: "Delete" }));
    expect(onDelete).toHaveBeenCalledOnce();
  });

  it("returns focus to the Actions trigger when a dialog opened from it closes", async () => {
    const user = userEvent.setup();
    render(<MenuWithDialog />);
    const trigger = screen.getByRole("button", { name: "Actions" });
    await user.tab();
    expect(trigger).toHaveFocus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(screen.getByRole("menuitem", { name: "Rename" })).toHaveFocus());
    await user.keyboard("{Enter}");
    const dialog = await screen.findByRole("dialog", { name: "Rename table" });
    await waitFor(() => expect(dialog).toContainElement(document.activeElement as HTMLElement));
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(trigger).toHaveFocus());
  });
});
