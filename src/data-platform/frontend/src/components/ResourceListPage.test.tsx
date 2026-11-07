import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { ResourceListPage } from "./ResourceListPage";

describe("ResourceListPage", () => {
  it("lists rows, opens the new form and confirms a delete by name", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    render(
      <MemoryRouter>
        <ResourceListPage
          title="Catalogs"
          breadcrumbs={[{ label: "Catalogs" }]}
          columns={[{ header: "Name", cell: (row: { name: string }) => row.name }]}
          rows={[{ name: "iceberg" }]}
          rowKey={(row) => row.name}
          newLabel="New catalog"
          renderForm={({ onClose }) => (
            <button type="button" onClick={onClose}>
              form open
            </button>
          )}
          objectKind="catalog"
          objectName={(row) => row.name}
          fullPath={(row) => row.name}
          onDelete={onDelete}
          deletePending={false}
          deleteError={null}
        />
      </MemoryRouter>,
    );
    expect(screen.getByText("iceberg")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "New catalog" }));
    expect(screen.getByRole("button", { name: "form open" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "form open" }));
    await user.click(screen.getByRole("button", { name: "Delete iceberg" }));
    await user.type(screen.getByLabelText(/type iceberg to confirm/i), "iceberg");
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(onDelete).toHaveBeenCalledWith({ name: "iceberg" });
  });
});
