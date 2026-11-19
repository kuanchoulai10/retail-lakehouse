import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { bodyOf, stubCatalogApi, type StubbedCall } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { RunMaintenanceDialog } from "./RunMaintenanceDialog";

const PATH = "/v1/tables/uuid-orders/maintenance";

function renderDialog(tablePriority: string): StubbedCall[] {
  const calls = stubCatalogApi({ [`POST ${PATH}`]: () => jsonResponse({ accepted: true }, 202) });
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <RunMaintenanceDialog tableUuid="uuid-orders" tablePriority={tablePriority} onClose={() => {}} />
    </QueryClientProvider>,
  );
  return calls;
}

describe("RunMaintenanceDialog", { timeout: 15_000 }, () => {
  it("defaults the priority to the table's own", () => {
    renderDialog("P1");
    expect(screen.getByRole("combobox", { name: "Priority" })).toHaveTextContent("P1");
  });

  it("sends no priority when the user does not change the table's", async () => {
    const user = userEvent.setup();
    const calls = renderDialog("P2");
    await user.click(screen.getByRole("button", { name: "Run" }));
    await waitFor(() =>
      expect(bodyOf(calls, "POST", PATH)).toEqual({
        operations: ["rewrite_data_files", "rewrite_manifests", "expire_snapshots", "remove_orphan_files"],
      }),
    );
  });

  it("sends no priority when the user picks another and then goes back to the table's", async () => {
    const user = userEvent.setup();
    const calls = renderDialog("P3");
    await user.click(screen.getByRole("combobox", { name: "Priority" }));
    await user.click(await screen.findByRole("option", { name: "P0 · urgent" }));
    await user.click(screen.getByRole("combobox", { name: "Priority" }));
    await user.click(await screen.findByRole("option", { name: "P3 · default" }));
    await user.click(screen.getByRole("button", { name: "Run" }));
    await waitFor(() => expect(bodyOf(calls, "POST", PATH)).not.toHaveProperty("priority"));
  });

  it("sends the priority the user picked", async () => {
    const user = userEvent.setup();
    const calls = renderDialog("P3");
    await user.click(screen.getByRole("combobox", { name: "Priority" }));
    expect(
      (await screen.findAllByRole("option")).map((option) => option.textContent),
    ).toEqual(["P0 · urgent", "P1", "P2", "P3 · default"]);
    await user.click(screen.getByRole("option", { name: "P0 · urgent" }));
    await user.click(screen.getByRole("button", { name: "Run" }));
    await waitFor(() =>
      expect(bodyOf(calls, "POST", PATH)).toEqual({
        operations: ["rewrite_data_files", "rewrite_manifests", "expire_snapshots", "remove_orphan_files"],
        priority: "P0",
      }),
    );
  });
});
