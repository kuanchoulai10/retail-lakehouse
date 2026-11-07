import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { ResourceListPage } from "./ResourceListPage";

interface Row {
  name: string;
}

function renderPage(onDelete: (row: Row) => Promise<void>, rows: Row[] = [{ name: "iceberg" }]) {
  render(
    <MemoryRouter>
      <ResourceListPage
        title="Catalogs"
        breadcrumbs={[{ label: "Catalogs" }]}
        columns={[{ header: "Name", cell: (row: Row) => row.name }]}
        rows={rows}
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
      />
    </MemoryRouter>,
  );
}

async function confirmDelete(user: ReturnType<typeof userEvent.setup>, name: string) {
  await user.click(screen.getByRole("button", { name: `Delete ${name}` }));
  await user.type(screen.getByLabelText(/to confirm/i), name);
  await user.click(screen.getByRole("button", { name: "Delete" }));
}

describe("ResourceListPage", () => {
  it("lists rows and opens the new form", async () => {
    const user = userEvent.setup();
    renderPage(vi.fn().mockResolvedValue(undefined));
    expect(screen.getByText("iceberg")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "New catalog" }));
    expect(screen.getByRole("button", { name: "form open" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "form open" }));
    expect(screen.queryByRole("button", { name: "form open" })).not.toBeInTheDocument();
  });

  it("closes the dialog after a delete resolves", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn().mockResolvedValue(undefined);
    renderPage(onDelete);
    await confirmDelete(user, "iceberg");
    expect(onDelete).toHaveBeenCalledWith({ name: "iceberg" });
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("keeps the dialog open and shows the error when a delete rejects", async () => {
    const user = userEvent.setup();
    renderPage(vi.fn().mockRejectedValue(new Error("Catalog is not empty")));
    await confirmDelete(user, "iceberg");
    expect(await screen.findByRole("alert")).toHaveTextContent("Catalog is not empty");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("does not show one row's failed delete on another row", async () => {
    const user = userEvent.setup();
    renderPage(vi.fn().mockRejectedValue(new Error("Catalog is not empty")), [
      { name: "a" },
      { name: "b" },
    ]);
    await confirmDelete(user, "a");
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    await user.click(screen.getByRole("button", { name: "Delete b" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
