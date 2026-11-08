import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FormDialog } from "./FormDialog";

function renderDialog(props: Partial<React.ComponentProps<typeof FormDialog>> = {}) {
  return render(
    <FormDialog
      title="New thing"
      description="Creates a thing."
      submitLabel="Create"
      isPending={false}
      error={null}
      onSubmit={() => {}}
      onClose={() => {}}
      {...props}
    >
      <input aria-label="Name" />
    </FormDialog>,
  );
}

describe("FormDialog", () => {
  it("lays its fields in a single column", () => {
    renderDialog();
    expect(screen.getByRole("form", { name: "New thing" })).toHaveClass("grid-cols-1");
  });

  it("submits through the submit button and cancels through Cancel", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    const onClose = vi.fn();
    renderDialog({ onSubmit, onClose });
    await user.click(screen.getByRole("button", { name: "Create" }));
    expect(onSubmit).toHaveBeenCalledOnce();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("shows the error and its action while the dialog stays open", () => {
    renderDialog({ error: "Conflict", errorAction: <button type="button">Reload</button> });
    expect(screen.getByRole("alert")).toHaveTextContent("Conflict");
    expect(screen.getByRole("button", { name: "Reload" })).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("disables submit while pending", () => {
    renderDialog({ isPending: true });
    expect(screen.getByRole("button", { name: "Create" })).toBeDisabled();
  });
});
