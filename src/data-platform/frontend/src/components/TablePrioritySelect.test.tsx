import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { TableApiResponse } from "../api/generated/model";
import { getGetTableQueryKey } from "../api/generated/tables/tables";
import { bodyOf, callsTo, stubCatalogApi, type StubHandler } from "../test/catalogApiStub";
import { jsonResponse, tableFixture } from "../test/fixtures";
import { TablePrioritySelect } from "./TablePrioritySelect";

const PATH = "/v1/tables/uuid-orders/priority";

function renderSelect(table: TableApiResponse = tableFixture()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidate = vi.spyOn(client, "invalidateQueries");
  render(
    <QueryClientProvider client={client}>
      <TablePrioritySelect table={table} />
    </QueryClientProvider>,
  );
  return { invalidate };
}

function stubPut(handler: StubHandler = () => jsonResponse(tableFixture({ priority: "P1" }))) {
  return stubCatalogApi({ [`PUT ${PATH}`]: handler });
}

describe("TablePrioritySelect", { timeout: 15_000 }, () => {
  it("shows the table's priority", () => {
    renderSelect(tableFixture({ priority: "P0" }));
    expect(screen.getByRole("combobox", { name: "Priority" })).toHaveTextContent("P0 · urgent");
  });

  it("offers P0 · urgent, P1, P2 and P3 · default", async () => {
    const user = userEvent.setup();
    renderSelect();
    await user.click(screen.getByRole("combobox", { name: "Priority" }));
    const options = await screen.findAllByRole("option");
    expect(options.map((option) => option.textContent)).toEqual(["P0 · urgent", "P1", "P2", "P3 · default"]);
  });

  it("choosing P1 puts the priority and refetches the table", async () => {
    const user = userEvent.setup();
    const calls = stubPut();
    const { invalidate } = renderSelect();
    await user.click(screen.getByRole("combobox", { name: "Priority" }));
    await user.click(await screen.findByRole("option", { name: "P1" }));
    await waitFor(() => expect(callsTo(calls, "PUT", PATH)).toHaveLength(1));
    expect(bodyOf(calls, "PUT", PATH)).toEqual({ priority: "P1" });
    await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: getGetTableQueryKey("uuid-orders") }));
  });

  it("keeps the old value and shows the error when the save fails", async () => {
    const user = userEvent.setup();
    stubPut(() => jsonResponse({ detail: "table is dropped" }, 409));
    const { invalidate } = renderSelect();
    await user.click(screen.getByRole("combobox", { name: "Priority" }));
    await user.click(await screen.findByRole("option", { name: "P1" }));
    expect(await screen.findByText(/Could not set the priority: table is dropped/)).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Priority" })).toHaveTextContent("P3 · default");
    expect(invalidate).toHaveBeenCalledWith({ queryKey: getGetTableQueryKey("uuid-orders") });
  });

  it("is read-only for a dropped table", () => {
    renderSelect(tableFixture({ status: "dropped" }));
    expect(screen.getByRole("combobox", { name: "Priority" })).toBeDisabled();
  });

  it("opens with Enter, moves with the arrows, picks with Enter, and Escape returns focus", async () => {
    const user = userEvent.setup();
    const calls = stubPut();
    renderSelect();
    const trigger = screen.getByRole("combobox", { name: "Priority" });
    await user.tab();
    expect(trigger).toHaveFocus();
    await user.keyboard("{Enter}");
    const current = await screen.findByRole("option", { name: "P3 · default" });
    await waitFor(() => expect(current).toHaveFocus());
    await user.keyboard("{ArrowUp}");
    await waitFor(() => expect(screen.getByRole("option", { name: "P2" })).toHaveFocus());
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("listbox")).not.toBeInTheDocument());
    await waitFor(() => expect(trigger).toHaveFocus());
    expect(calls).toEqual([]);
    await user.keyboard(" ");
    await screen.findByRole("listbox");
    await user.keyboard("{ArrowUp}{ArrowUp}{Enter}");
    await waitFor(() => expect(bodyOf(calls, "PUT", PATH)).toEqual({ priority: "P1" }));
  });
});
