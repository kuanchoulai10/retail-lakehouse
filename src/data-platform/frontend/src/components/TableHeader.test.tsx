import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { catalogTableFixture } from "../test/catalogApiStub";
import { jsonResponse, tableFixture } from "../test/fixtures";
import { TableHeader } from "./TableHeader";

function newClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderHeader(status = "active", client = newClient(), extra: React.ReactNode = null) {
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <TableHeader table={catalogTableFixture()} managed={tableFixture({ status })} menuItems={[]} />
        {extra}
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function HealthProbe({ queryFn }: { queryFn: () => Promise<unknown> }) {
  useQuery({ queryKey: ["health", "uuid-orders"], queryFn });
  return null;
}

describe("TableHeader", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(tableFixture())));
  });

  it("shows the name, status, preset and rule", () => {
    renderHeader();
    expect(screen.getByRole("heading", { level: 1, name: "orders" })).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText(/Preset: default/)).toBeInTheDocument();
    expect(screen.getByText(/Rule: rule-1/)).toBeInTheDocument();
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

  it("posts /pause when Pause is clicked", async () => {
    const user = userEvent.setup();
    renderHeader();
    await user.click(screen.getByRole("button", { name: "Pause" }));
    const call = vi.mocked(fetch).mock.calls[0];
    expect(call?.[0]).toBe("/console/api/v1/tables/uuid-orders/pause");
    expect((call?.[1] as RequestInit).method).toBe("POST");
  });

  it("posts /resume when the table is paused", async () => {
    const user = userEvent.setup();
    renderHeader("paused");
    await user.click(screen.getByRole("button", { name: "Resume" }));
    expect(vi.mocked(fetch).mock.calls[0]?.[0]).toBe(
      "/console/api/v1/tables/uuid-orders/resume",
    );
  });

  it("refetches health after Pause", async () => {
    const user = userEvent.setup();
    const healthFn = vi.fn().mockResolvedValue({});
    renderHeader("active", newClient(), <HealthProbe queryFn={healthFn} />);
    await vi.waitFor(() => expect(healthFn).toHaveBeenCalledTimes(1));
    await user.click(screen.getByRole("button", { name: "Pause" }));
    await vi.waitFor(() => expect(healthFn).toHaveBeenCalledTimes(2));
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

  it("marks runs and health stale after a maintenance trigger", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ accepted: true }, 202)));
    const client = newClient();
    client.setQueryData(["runs", "uuid-orders"], []);
    client.setQueryData(["health", "uuid-orders"], {});
    renderHeader("active", client);
    await user.click(screen.getByRole("button", { name: "Run maintenance" }));
    await user.click(screen.getByRole("button", { name: "Run" }));
    await vi.waitFor(() => {
      expect(client.getQueryState(["runs", "uuid-orders"])?.isInvalidated).toBe(true);
      expect(client.getQueryState(["health", "uuid-orders"])?.isInvalidated).toBe(true);
    });
  });

  it("disables Run maintenance unless the table is active", () => {
    renderHeader("paused");
    const button = screen.getByRole("button", { name: "Run maintenance" });
    expect(button).toBeDisabled();
    expect(button).toHaveAccessibleDescription("Only an active table can run maintenance");
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
    expect(fetch).not.toHaveBeenCalled();
  });

  it("gives the disabled phone overflow item the same reason as the button", async () => {
    const user = userEvent.setup();
    renderHeader("paused");
    await user.click(screen.getByRole("button", { name: "More actions" }));
    const item = await screen.findByRole("menuitem", { name: "Run maintenance" });
    expect(item).toHaveAttribute("aria-disabled", "true");
    expect(item).toHaveAccessibleDescription("Only an active table can run maintenance");
  });

  it("enables Run maintenance on an active table", () => {
    renderHeader("active");
    expect(screen.getByRole("button", { name: "Run maintenance" })).toBeEnabled();
  });

  it("posts the checked operations from the run maintenance dialog", async () => {
    const user = userEvent.setup();
    renderHeader();
    await user.click(screen.getByRole("button", { name: "Run maintenance" }));
    expect(screen.getByText("Runs on the whole table, ignoring thresholds")).toBeInTheDocument();
    await user.click(screen.getByLabelText("expire_snapshots"));
    await user.click(screen.getByRole("button", { name: "Run" }));
    const call = vi.mocked(fetch).mock.calls[0];
    expect(call?.[0]).toBe("/console/api/v1/tables/uuid-orders/maintenance");
    expect(JSON.parse((call?.[1] as RequestInit).body as string)).toEqual({
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
