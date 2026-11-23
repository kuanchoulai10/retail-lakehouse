import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { TableMaintenanceRunApiResponse } from "../api/generated/model";
import { getListTableMaintenanceRunsQueryKey } from "../api/generated/table-maintenance-runs/table-maintenance-runs";
import { bodyOf, stubCatalogApi, type StubbedCall, type StubHandler } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { RunMaintenanceDialog } from "./RunMaintenanceDialog";

const PATH = "/v1/tables/uuid-orders/maintenance";

const RUNS_PATH = "/v1/tables/uuid-orders/table-maintenance-runs?limit=1";
const IN_FLIGHT_NOTE =
  "A maintenance run is already in flight. Running now does not start another run: it raises that run's priority if you pick a higher one. The operations you pick are not added to it.";

function runWithStatus(status: string): TableMaintenanceRunApiResponse {
  return {
    run_id: "mr-1",
    table_uuid: "uuid-orders",
    execution_ref: "table-maintenance:table-uuid=uuid-orders",
    trigger: "manual",
    priority: "P3",
    operation: "rewrite_data_files",
    status,
    created_at: "2026-11-20T10:00:00Z",
    started_at: null,
    finished_at: null,
    settings: {},
    partitions: [],
    metrics: {},
    error: null,
    skip_reason: null,
    attempts: [],
  };
}

let queryClient: QueryClient;

function renderDialog(
  tablePriority: string,
  newestRun: TableMaintenanceRunApiResponse | null = null,
  readNewestRun: StubHandler = () => jsonResponse(newestRun === null ? [] : [newestRun]),
): StubbedCall[] {
  const calls = stubCatalogApi({
    [`POST ${PATH}`]: () => jsonResponse({ accepted: true }, 202),
    [`GET ${RUNS_PATH}`]: readNewestRun,
  });
  queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
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

  it.each(["pending", "queued", "running"])("says a %s newest run is already in flight", async (status) => {
    renderDialog("P3", runWithStatus(status));
    expect(await screen.findByText(IN_FLIGHT_NOTE)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run" })).toBeEnabled();
  });

  it.each(["succeeded", "failed"])("says nothing when the newest run %s", async (status) => {
    renderDialog("P3", runWithStatus(status));
    await waitFor(() =>
      expect(queryClient.getQueryState(getListTableMaintenanceRunsQueryKey("uuid-orders", { limit: 1 }))?.status).toBe(
        "success",
      ),
    );
    expect(screen.queryByText(IN_FLIGHT_NOTE)).not.toBeInTheDocument();
  });

  it("says nothing and still runs when reading the newest run fails", async () => {
    const user = userEvent.setup();
    const calls = renderDialog("P3", null, () => jsonResponse({ detail: "runs unavailable" }, 500));
    await waitFor(() =>
      expect(queryClient.getQueryState(getListTableMaintenanceRunsQueryKey("uuid-orders", { limit: 1 }))?.status).toBe(
        "error",
      ),
    );
    expect(screen.queryByText(IN_FLIGHT_NOTE)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "Run" }));
    await waitFor(() => expect(bodyOf(calls, "POST", PATH)).toBeDefined());
  });

  it("says nothing and still runs while reading the newest run has not answered", async () => {
    const user = userEvent.setup();
    const calls = renderDialog("P3", null, () => new Promise<Response>(() => {}));
    await waitFor(() => expect(calls.some((call) => call.path === RUNS_PATH)).toBe(true));
    expect(screen.queryByText(IN_FLIGHT_NOTE)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Run" }));
    await waitFor(() => expect(bodyOf(calls, "POST", PATH)).toBeDefined());
  });

  it("asks for the table's newest run only", async () => {
    const calls = renderDialog("P3", runWithStatus("queued"));
    await screen.findByText(IN_FLIGHT_NOTE);
    expect(calls.filter((call) => call.method === "GET").map((call) => call.path)).toEqual([RUNS_PATH]);
  });

  it("reads the newest run again on mount even when the cache is fresh and the client keeps data for long", async () => {
    const calls = stubCatalogApi({
      [`GET ${RUNS_PATH}`]: () => jsonResponse([runWithStatus("running")]),
    });
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
    queryClient.setQueryData(getListTableMaintenanceRunsQueryKey("uuid-orders", { limit: 1 }), [
      runWithStatus("succeeded"),
    ]);
    render(
      <QueryClientProvider client={queryClient}>
        <RunMaintenanceDialog tableUuid="uuid-orders" tablePriority="P3" onClose={() => {}} />
      </QueryClientProvider>,
    );
    await waitFor(() => expect(calls.filter((call) => call.path === RUNS_PATH)).toHaveLength(1));
    expect(await screen.findByText(IN_FLIGHT_NOTE)).toBeInTheDocument();
  });

  it("puts the in-flight note after the Priority control", async () => {
    renderDialog("P3", runWithStatus("queued"));
    const note = await screen.findByText(IN_FLIGHT_NOTE);
    const priority = screen.getByRole("combobox", { name: "Priority" });
    const checkbox = screen.getByRole("checkbox", { name: "remove_orphan_files" });
    expect(checkbox.compareDocumentPosition(note) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(priority.compareDocumentPosition(note) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("keeps the in-flight note out of the tab order: the operations and Run stay reachable", async () => {
    const user = userEvent.setup();
    renderDialog("P3", runWithStatus("queued"));
    const note = await screen.findByText(IN_FLIGHT_NOTE);
    const visited: Element[] = [];
    for (let step = 0; step < 12 && document.activeElement !== screen.getByRole("button", { name: "Run" }); step++) {
      await user.tab();
      visited.push(document.activeElement!);
    }
    expect(visited).toContain(screen.getByRole("checkbox", { name: "rewrite_data_files" }));
    expect(visited).toContain(screen.getByRole("checkbox", { name: "remove_orphan_files" }));
    expect(visited.at(-1)).toBe(screen.getByRole("button", { name: "Run" }));
    expect(visited.some((element) => note.contains(element))).toBe(false);
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
