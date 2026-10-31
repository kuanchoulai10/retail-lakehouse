import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { jsonResponse, metadataFixture, tableFixture } from "../test/fixtures";
import { TableHeader } from "./TableHeader";

function renderHeader(status = "active") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <TableHeader table={tableFixture({ status })} metadata={metadataFixture()} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TableHeader", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(tableFixture())));
  });

  it("shows the name, status, preset and rule", () => {
    renderHeader();
    expect(screen.getByText("iceberg.inventory.orders")).toBeInTheDocument();
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();
    expect(screen.getByText(/Preset: default/)).toBeInTheDocument();
    expect(screen.getByText(/Rule: rule-1/)).toBeInTheDocument();
  });

  it("shows the summary numbers from the metadata", () => {
    renderHeader();
    expect(screen.getByText("1,204,331 rows")).toBeInTheDocument();
    expect(screen.getByText("100 data files")).toBeInTheDocument();
    expect(screen.getByText("320.0 MB")).toBeInTheDocument();
    expect(screen.getByText("avg 3.2 MB / file")).toBeInTheDocument();
    expect(screen.getByText("17 snapshots")).toBeInTheDocument();
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
