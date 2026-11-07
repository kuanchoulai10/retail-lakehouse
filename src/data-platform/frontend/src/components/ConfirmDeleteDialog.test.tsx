import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ConfirmDeleteDialog } from "./ConfirmDeleteDialog";

function renderDialog(props: Partial<React.ComponentProps<typeof ConfirmDeleteDialog>> = {}) {
  const onConfirm = vi.fn();
  render(
    <ConfirmDeleteDialog
      open
      onOpenChange={() => {}}
      objectKind="table"
      objectName="orders"
      fullPath="iceberg.inventory.orders"
      onConfirm={onConfirm}
      isPending={false}
      error={null}
      {...props}
    />,
  );
  return onConfirm;
}

describe("ConfirmDeleteDialog", () => {
  it("delete stays disabled until the exact name is typed", async () => {
    const user = userEvent.setup();
    const onConfirm = renderDialog();
    expect(screen.getByText("iceberg.inventory.orders")).toBeInTheDocument();
    const button = screen.getByRole("button", { name: "Delete" });
    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText(/type orders to confirm/i), "order");
    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText(/type orders to confirm/i), "s");
    expect(button).toBeEnabled();
    await user.click(button);
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("shows the polaris error and stays open", () => {
    const onOpenChange = vi.fn();
    renderDialog({ error: new Error("Namespace is not empty"), onOpenChange });
    expect(screen.getByRole("alert")).toHaveTextContent("Namespace is not empty");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(onOpenChange).not.toHaveBeenCalled();
  });
});
