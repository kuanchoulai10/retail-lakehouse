import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ActionsMenu } from "./ActionsMenu";

describe("ActionsMenu", () => {
  it("runs the selected item", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    render(<ActionsMenu items={[{ label: "Delete", onSelect: onDelete }]} />);
    await user.click(screen.getByRole("button", { name: "Actions" }));
    await user.click(screen.getByRole("menuitem", { name: "Delete" }));
    expect(onDelete).toHaveBeenCalledOnce();
  });
});
