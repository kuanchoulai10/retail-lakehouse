import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ConfirmDeleteDialog } from "./ConfirmDeleteDialog";

type Props = React.ComponentProps<typeof ConfirmDeleteDialog>;

function dialog(props: Partial<Props> = {}) {
  return (
    <ConfirmDeleteDialog
      open
      onOpenChange={() => {}}
      objectKind="table"
      objectName="orders"
      fullPath="iceberg.inventory.orders"
      onConfirm={() => {}}
      isPending={false}
      error={null}
      {...props}
    />
  );
}

describe("ConfirmDeleteDialog", () => {
  it("delete stays disabled until the exact name is typed", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(dialog({ onConfirm }));
    expect(screen.getByText("iceberg.inventory.orders")).toBeInTheDocument();
    const button = screen.getByRole("button", { name: "Delete" });
    const input = screen.getByLabelText(/type orders to confirm/i);
    expect(button).toBeDisabled();
    await user.type(input, "order");
    expect(button).toBeDisabled();
    await user.type(input, "s");
    expect(button).toBeEnabled();
    await user.click(button);
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it.each(["Orders", "orders "])("stays disabled for the near miss %j", async (typed) => {
    const user = userEvent.setup();
    render(dialog());
    await user.type(screen.getByLabelText(/type orders to confirm/i), typed);
    expect(screen.getByRole("button", { name: "Delete" })).toBeDisabled();
  });

  it("shows the polaris error and stays open", () => {
    const onOpenChange = vi.fn();
    const { rerender } = render(dialog({ onOpenChange }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    rerender(dialog({ onOpenChange, error: new Error("Namespace is not empty") }));
    expect(screen.getByRole("alert")).toHaveTextContent("Namespace is not empty");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(onOpenChange).not.toHaveBeenCalled();
  });
});
