import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getListTableMaintenanceRunsQueryKey } from "../api/generated/table-maintenance-runs/table-maintenance-runs";
import { getListTableReconciliationsQueryKey } from "../api/generated/table-reconciliations/table-reconciliations";
import type { TableApiResponse } from "../api/generated/model";
import { bodyOf, catalogTableFixture, stubCatalogApi, type StubbedCall } from "../test/catalogApiStub";
import { jsonResponse, tableFixture } from "../test/fixtures";
import { TableHeader } from "./TableHeader";

function newClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderHeader(
  status = "managed",
  client = newClient(),
  extra: React.ReactNode = null,
  managed: Partial<TableApiResponse> = {},
) {
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <TableHeader table={catalogTableFixture()} managed={tableFixture({ status, ...managed })} menuItems={[]} />
        {extra}
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TableHeader", () => {
  let calls: StubbedCall[];

  beforeEach(() => {
    calls = stubCatalogApi({
      "POST /v1/tables/uuid-orders/maintenance": () => jsonResponse({ accepted: true }, 202),
      "POST /v1/tables/uuid-orders/reconcile": () => jsonResponse({ accepted: true }, 202),
    });
  });

  it("Reconcile now posts and refreshes reconciliations", async () => {
    const user = userEvent.setup();
    const client = newClient();
    const key = [...getListTableReconciliationsQueryKey("uuid-orders"), "pages"];
    client.setQueryData(key, { pages: [], pageParams: [] });
    renderHeader("managed", client);
    await user.click(screen.getByRole("button", { name: "Reconcile now" }));
    await vi.waitFor(() => expect(calls[0]).toMatchObject({ method: "POST", path: "/v1/tables/uuid-orders/reconcile" }));
    await vi.waitFor(() => expect(client.getQueryState(key)?.isInvalidated).toBe(true));
  });

  it("confirms Reconcile now and refreshes reconciliations again after a delay", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      const client = newClient();
      const key = [...getListTableReconciliationsQueryKey("uuid-orders"), "pages"];
      client.setQueryData(key, { pages: [], pageParams: [] });
      renderHeader("managed", client);
      await user.click(screen.getByRole("button", { name: "Reconcile now" }));
      expect(await screen.findByText("Reconciliation requested.")).toBeInTheDocument();
      await vi.waitFor(() => expect(client.getQueryState(key)?.isInvalidated).toBe(true));
      client.setQueryData(key, { pages: [], pageParams: [] });
      expect(client.getQueryState(key)?.isInvalidated).toBe(false);
      await vi.advanceTimersByTimeAsync(3000);
      expect(client.getQueryState(key)?.isInvalidated).toBe(true);
    } finally {
      vi.useRealTimers();
    }
  });

  it("shows the API detail when Reconcile now is refused", async () => {
    calls = stubCatalogApi({
      "POST /v1/tables/uuid-orders/reconcile": () => jsonResponse({ detail: "table is unmanaged" }, 409),
    });
    const user = userEvent.setup();
    renderHeader();
    await user.click(screen.getByRole("button", { name: "Reconcile now" }));
    expect(await screen.findByText("Could not reconcile the table: table is unmanaged")).toBeInTheDocument();
  });

  it("shows the name and no maintenance status, dry run, policy or rule", () => {
    renderHeader();
    expect(screen.getByRole("heading", { level: 1, name: "orders" })).toBeInTheDocument();
    expect(screen.queryByText("Managed")).not.toBeInTheDocument();
    expect(screen.queryByText("Dry run")).not.toBeInTheDocument();
    expect(screen.queryByText(/Policy:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Rule:/)).not.toBeInTheDocument();
    expect(screen.queryByText("dr-01m7s6c3tqee0rhg00xn5s97gw")).not.toBeInTheDocument();
  });

  it.each(["managed", "unmanaged"])("shows the same six numbers for a %s table", (status) => {
    renderHeader(status);
    for (const fact of ["1,204,331 rows", "100 data files", "320.0 MB", "avg 3.2 MB / file", "2 snapshots", "last commit 3 h ago"]) {
      expect(screen.getByText(fact)).toBeInTheDocument();
    }
  });

  it("shows the summary numbers from the catalog", () => {
    renderHeader();
    expect(screen.getByText("1,204,331 rows")).toBeInTheDocument();
    expect(screen.getByText("100 data files")).toBeInTheDocument();
    expect(screen.getByText("320.0 MB")).toBeInTheDocument();
    expect(screen.getByText("avg 3.2 MB / file")).toBeInTheDocument();
    expect(screen.getByText("2 snapshots")).toBeInTheDocument();
    expect(screen.getByText("last commit 3 h ago")).toBeInTheDocument();
  });

  it("offers no Pause or Resume: the discovery rules alone decide what is managed", async () => {
    const user = userEvent.setup();
    renderHeader();
    expect(screen.queryByRole("button", { name: "Pause" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Resume" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "More actions" }));
    expect(await screen.findByRole("menuitem", { name: "Reconcile now" })).toBeInTheDocument();
    expect(screen.queryByRole("menuitem", { name: /Pause|Resume/ })).not.toBeInTheDocument();
  });

  it("returns focus to Run maintenance after Escape", async () => {
    const user = userEvent.setup();
    renderHeader();
    const trigger = screen.getByRole("button", { name: "Run maintenance" });
    await user.click(trigger);
    await user.keyboard("{Escape}");
    await vi.waitFor(() => expect(trigger).toHaveFocus());
  });

  it("returns focus to Run maintenance after Cancel", async () => {
    const user = userEvent.setup();
    renderHeader();
    const trigger = screen.getByRole("button", { name: "Run maintenance" });
    await user.click(trigger);
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    await vi.waitFor(() => expect(trigger).toHaveFocus());
  });

  it("marks runs stale after a maintenance trigger", async () => {
    const user = userEvent.setup();
    const client = newClient();
    client.setQueryData(getListTableMaintenanceRunsQueryKey("uuid-orders"), []);
    renderHeader("managed", client);
    await user.click(screen.getByRole("button", { name: "Run maintenance" }));
    await user.click(screen.getByRole("button", { name: "Run" }));
    await vi.waitFor(() => {
      expect(client.getQueryState(getListTableMaintenanceRunsQueryKey("uuid-orders"))?.isInvalidated).toBe(true);
    });
  });

  it("disables Run maintenance unless the table is managed", () => {
    renderHeader("unmanaged");
    const button = screen.getByRole("button", { name: "Run maintenance" });
    expect(button).toBeDisabled();
    expect(button).toHaveAccessibleDescription("Only a managed table can run maintenance");
  });

  it("wraps a long title on a phone and truncates it from md so it cannot overflow", () => {
    renderHeader();
    expect(screen.getByRole("heading", { level: 1 })).toHaveClass("[overflow-wrap:anywhere]", "md:truncate");
  });

  it("opens the dialog as role dialog and closes it on Escape without posting", async () => {
    const user = userEvent.setup();
    renderHeader();
    await user.click(screen.getByRole("button", { name: "Run maintenance" }));
    expect(screen.getByRole("dialog", { name: "Run maintenance" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(calls).toEqual([]);
  });

  it("gives the disabled phone overflow item the same reason as the button", async () => {
    const user = userEvent.setup();
    renderHeader("unmanaged");
    await user.click(screen.getByRole("button", { name: "More actions" }));
    const item = await screen.findByRole("menuitem", { name: "Run maintenance" });
    expect(item).toHaveAttribute("aria-disabled", "true");
    expect(item).toHaveAccessibleDescription("Only a managed table can run maintenance");
  });

  it("enables Run maintenance on a managed table", () => {
    renderHeader("managed");
    expect(screen.getByRole("button", { name: "Run maintenance" })).toBeEnabled();
  });

  it("posts the checked operations from the run maintenance dialog", async () => {
    const user = userEvent.setup();
    renderHeader();
    await user.click(screen.getByRole("button", { name: "Run maintenance" }));
    expect(screen.getByText("Runs on the whole table, ignoring thresholds")).toBeInTheDocument();
    await user.click(screen.getByLabelText("expire_snapshots"));
    await user.click(screen.getByRole("button", { name: "Run" }));
    await vi.waitFor(() => expect(calls[0]?.path).toBe("/v1/tables/uuid-orders/maintenance"));
    expect(bodyOf(calls, "POST", "/v1/tables/uuid-orders/maintenance")).toEqual({
      operations: ["rewrite_data_files", "rewrite_manifests", "remove_orphan_files"],
    });
  });

  it("preselects only initialOperations in the dialog", async () => {
    const { RunMaintenanceDialog } = await import("./RunMaintenanceDialog");
    const client = new QueryClient();
    render(
      <QueryClientProvider client={client}>
        <RunMaintenanceDialog
          tableUuid="uuid-orders"
          initialOperations={["expire_snapshots"]}
          onClose={() => {}}
        />
      </QueryClientProvider>,
    );
    expect(screen.getByLabelText("expire_snapshots")).toBeChecked();
    expect(screen.getByLabelText("rewrite_data_files")).not.toBeChecked();
  });
});

describe("TableHeader of an unmanaged table", () => {
  it("Reconcile now is hidden for an unmanaged table", () => {
    render(
      <QueryClientProvider client={newClient()}>
        <MemoryRouter>
          <TableHeader table={catalogTableFixture()} managed={null} menuItems={[]} />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(screen.queryByRole("button", { name: "Reconcile now" })).not.toBeInTheDocument();
  });

  it("shows the catalog numbers and the menu but no maintenance actions", () => {
    render(
      <QueryClientProvider client={newClient()}>
        <MemoryRouter>
          <TableHeader
            table={catalogTableFixture()}
            managed={null}
            menuItems={[{ label: "Rename", onSelect: () => {} }]}
          />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(screen.getByText("1,204,331 rows")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Actions" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Run maintenance" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Pause" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Preset:/)).not.toBeInTheDocument();
  });
});
