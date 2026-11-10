import { TooltipProvider } from "@retail-lakehouse/design-system";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it } from "vitest";
import type {
  ReconciliationOperationApiResponse,
  TableReconciliationApiResponse,
} from "../../api/generated/model";
import { stubCatalogApi, type StubbedCall } from "../../test/catalogApiStub";
import { jsonResponse } from "../../test/fixtures";
import { ReconciliationsTab } from "./ReconciliationsTab";

// Local times, so each record lands on the same day and clock time in any time zone.
function at(day: number, hour: number, minute = 42): string {
  return new Date(2026, 10, day, hour, minute).toISOString();
}

function op(overrides: Partial<ReconciliationOperationApiResponse>): ReconciliationOperationApiResponse {
  return { operation: "rewrite_manifests", result: "not_needed", combine: "all", measurements: [], next_eligible_at: null, ...overrides };
}

const QUIET_OPERATIONS = [
  op({
    operation: "rewrite_data_files",
    measurements: [{ key: "reducible_files", observed: 2, unit: "count", threshold: 5, comparison: ">=", met: false }],
  }),
  op({
    operation: "rewrite_manifests",
    measurements: [{ key: "small_manifests", observed: 12, unit: "count", threshold: 20, comparison: ">=", met: false }],
  }),
  op({
    operation: "expire_snapshots",
    measurements: [{ key: "expirable_snapshots", observed: 0, unit: "count", threshold: 1, comparison: ">=", met: false }],
  }),
  op({ operation: "remove_orphan_files", result: "off" }),
];

function quiet(id: string, reconciledAt: string): TableReconciliationApiResponse {
  return {
    reconciliation_id: id,
    table_uuid: "uuid-orders",
    reconciled_at: reconciledAt,
    wake_reasons: { schedule: 1 },
    dry_run: false,
    outcome: "planned",
    skip_reason: null,
    operations: QUIET_OPERATIONS,
    run_id: null,
  };
}

const RUN_ID = "0b9e3c1a-2f4d-4c8e-9a1b-5d6e7f8a9b0c";

const STARTED: TableReconciliationApiResponse = {
  ...quiet("rec-started", at(10, 10)),
  wake_reasons: { catalog_commit: 3, schedule: 1 },
  run_id: RUN_ID,
  operations: [
    op({
      operation: "remove_orphan_files",
      result: "cooling_down",
      next_eligible_at: new Date(2026, 10, 14, 3, 0).toISOString(),
    }),
    op({
      operation: "expire_snapshots",
      measurements: [{ key: "expirable_snapshots", observed: 0, unit: "count", threshold: 1, comparison: ">=", met: false }],
    }),
    op({
      operation: "rewrite_data_files",
      result: "started",
      measurements: [
        { key: "reducible_files", observed: 1240, unit: "count", threshold: 5, comparison: ">=", met: true },
        { key: "target_file_size", observed: 134217728, unit: "bytes", threshold: null, comparison: null, met: null },
        { key: "qualifying_partitions", observed: 3, unit: "count", threshold: null, comparison: null, met: null },
      ],
    }),
    op({ operation: "rewrite_manifests", result: "off" }),
  ],
};

const DRY_RUN: TableReconciliationApiResponse = {
  ...quiet("rec-dry", at(10, 2)),
  dry_run: true,
  operations: [
    op({
      operation: "rewrite_data_files",
      result: "would_start",
      measurements: [{ key: "reducible_files", observed: 620, unit: "count", threshold: 5, comparison: ">=", met: true }],
    }),
    ...QUIET_OPERATIONS.slice(1),
  ],
};

function renderTab() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/tables/orders/reconciliations"]}>
        <TooltipProvider>
          <Routes>
            <Route path="/tables/:table/:tab" element={<ReconciliationsTab tableUuid="uuid-orders" />} />
          </Routes>
        </TooltipProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function stubList(items: TableReconciliationApiResponse[]): StubbedCall[] {
  return stubCatalogApi({ "GET /v1/tables/uuid-orders/reconciliations*": () => jsonResponse(items) });
}

function hours(day: number, from: number, to: number): TableReconciliationApiResponse[] {
  const out: TableReconciliationApiResponse[] = [];
  for (let hour = to; hour >= from; hour -= 1) out.push(quiet(`rec-${day}-${hour}`, at(day, hour)));
  return out;
}

async function openDrawer(user: ReturnType<typeof userEvent.setup>, name: RegExp): Promise<HTMLElement> {
  await user.click(await screen.findByRole("button", { name }));
  return screen.findByRole("dialog");
}

describe("ReconciliationsTab", () => {
  beforeEach(() => {
    stubList([STARTED, ...hours(10, 3, 9), quiet("rec-9", at(9, 23))]);
  });

  it("groups records by day under h2 headings", async () => {
    renderTab();
    await screen.findByRole("region", { name: "Reconciliations on Nov 10, 2026" });
    expect(screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent)).toEqual([
      "Reconciliations on Nov 10, 2026",
      "Reconciliations on Nov 9, 2026",
    ]);
  });

  it("folds seven quiet records into one line", async () => {
    const user = userEvent.setup();
    renderTab();
    const fold = await screen.findByRole("button", { name: "7 reconciliations found nothing to do, 03:42–09:42" });
    expect(fold).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("button", { name: /Schedule at 05:42/ })).not.toBeInTheDocument();

    await user.click(fold);

    expect(fold).toHaveAttribute("aria-expanded", "true");
    const dialog = await openDrawer(user, /Schedule at 05:42/);
    expect(within(dialog).getByRole("heading", { name: "Nothing to do" })).toBeInTheDocument();
  });

  it("a started record breaks the fold", async () => {
    stubList([...hours(10, 7, 9), { ...STARTED, reconciled_at: at(10, 6, 50) }, ...hours(10, 1, 6)]);
    renderTab();
    const day = await screen.findByRole("region", { name: "Reconciliations on Nov 10, 2026" });
    const lines = within(day).getAllByRole("listitem").map((li) => li.textContent ?? "");
    expect(lines).toHaveLength(3);
    expect(lines[0]).toContain("3 reconciliations found nothing to do, 07:42–09:42");
    expect(lines[1]).toContain("Started Rewrite data files");
    expect(lines[2]).toContain("6 reconciliations found nothing to do, 01:42–06:42");
  });

  it("consecutive paused skips fold into one line", async () => {
    const skip = (id: string, hour: number): TableReconciliationApiResponse => ({
      ...quiet(id, at(10, hour)),
      outcome: "skipped",
      skip_reason: "paused",
      operations: [],
    });
    stubList([...hours(10, 6, 7), skip("s5", 5), skip("s4", 4), skip("s3", 3), ...hours(10, 1, 2)]);
    renderTab();
    const day = await screen.findByRole("region", { name: "Reconciliations on Nov 10, 2026" });
    const lines = within(day).getAllByRole("listitem").map((li) => li.textContent ?? "");
    expect(lines).toEqual([
      "2 reconciliations found nothing to do, 06:42–07:42",
      "3 reconciliations skipped: table paused, 03:42–05:42",
      "2 reconciliations found nothing to do, 01:42–02:42",
    ]);
  });

  it("shows a lone quiet record as its own line", async () => {
    stubList([STARTED, quiet("rec-lone", at(10, 9))]);
    renderTab();
    expect(await screen.findByRole("button", { name: /^Nothing to do/ })).toBeInTheDocument();
    expect(screen.queryByText(/reconciliations found nothing to do/)).not.toBeInTheDocument();
  });

  it("dry run record shows Would start and a Dry run badge", async () => {
    stubList([DRY_RUN]);
    renderTab();
    const row = await screen.findByRole("button", { name: /Would start Rewrite data files/ });
    expect(within(row).getByText("Dry run")).toBeInTheDocument();
  });

  it("names the main wake reason and the time on each line", async () => {
    renderTab();
    expect(await screen.findByRole("button", { name: /Started Rewrite data files.*Catalog commit × 3 at 10:42/ })).toBeInTheDocument();
  });

  it("drawer shows wake reasons with counts", async () => {
    const user = userEvent.setup();
    renderTab();
    const dialog = await openDrawer(user, /Started Rewrite data files/);
    expect(within(dialog).getByRole("heading", { name: "Started Rewrite data files" })).toBeInTheDocument();
    expect(within(dialog).getByText(/Catalog commit × 3, Schedule/)).toBeInTheDocument();
  });

  it("drawer lists operations in result order", async () => {
    const user = userEvent.setup();
    renderTab();
    const dialog = await openDrawer(user, /Started Rewrite data files/);
    expect(within(dialog).getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual([
      "Rewrite data files",
      "Expire snapshots",
      "Remove orphan files",
      "Rewrite manifests",
    ]);
    const compaction = within(dialog).getByRole("region", { name: "Rewrite data files" });
    expect(within(compaction).getByText("Started")).toBeInTheDocument();
    const orphan = within(dialog).getByRole("region", { name: "Remove orphan files" });
    expect(within(orphan).getByText("Cooling down")).toBeInTheDocument();
  });

  it("reason sentence cites only deciding measurements", async () => {
    const user = userEvent.setup();
    renderTab();
    const dialog = await openDrawer(user, /Started Rewrite data files/);
    const compaction = within(dialog).getByRole("region", { name: "Rewrite data files" });
    expect(within(compaction).getByText("Because reducible files 1,240 across 3 partitions (needs ≥ 5 per partition).")).toBeInTheDocument();
    expect(within(compaction).queryByText(/target file size/i)).not.toBeInTheDocument();
  });

  it("All measurements lists context measurements without a met mark", async () => {
    const user = userEvent.setup();
    renderTab();
    const dialog = await openDrawer(user, /Started Rewrite data files/);
    const compaction = within(dialog).getByRole("region", { name: "Rewrite data files" });
    const toggle = within(compaction).getByRole("button", { name: "All measurements" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    await user.click(toggle);

    const list = within(compaction).getByRole("list", { name: "All measurements of Rewrite data files" });
    const [reducible, target, partitions] = within(list).getAllByRole("listitem") as [HTMLElement, HTMLElement, HTMLElement];
    expect(reducible).toHaveTextContent(/Reducible files.*1,240.*≥ 5/);
    expect(reducible).toHaveTextContent(/^Met:/);
    expect(reducible).not.toHaveTextContent(/Not met/);
    expect(target).toHaveTextContent(/Target file size.*128\.0 MB/);
    expect(target).not.toHaveTextContent(/met:/i);
    expect(partitions).not.toHaveTextContent(/met:/i);
  });

  it("run link points at the maintenance tab with the run id", async () => {
    const user = userEvent.setup();
    renderTab();
    const row = (await screen.findByRole("button", { name: /Started Rewrite data files/ })).closest("li") as HTMLElement;
    const lineLink = within(row).getByRole("link", { name: `Open maintenance run ${RUN_ID}` });
    expect(lineLink).toHaveAttribute("href", `/tables/orders/maintenance?run=${RUN_ID}`);
    expect(lineLink).toHaveTextContent(/^Run 0b9e3c1a$/);
    expect(within(lineLink).getByText("0b9e3c1a")).toHaveClass("font-mono");
    const dialog = await openDrawer(user, /Started Rewrite data files/);
    const drawerLink = within(dialog).getByRole("link", { name: `Open maintenance run ${RUN_ID}` });
    expect(drawerLink).toHaveAttribute("href", `/tables/orders/maintenance?run=${RUN_ID}`);
    expect(drawerLink).toHaveTextContent(/^Open maintenance run 0b9e3c1a$/);
  });

  it("draws an open timeline: a filled marker for what started, outlined for others, dashed for a fold", async () => {
    stubList([STARTED, quiet("rec-lone", at(10, 9)), { ...DRY_RUN, reconciled_at: at(10, 8) }, ...hours(10, 1, 3)]);
    renderTab();
    const day = await screen.findByRole("region", { name: "Reconciliations on Nov 10, 2026" });
    expect(within(day).getByRole("heading", { level: 2 })).toHaveTextContent(/Nov 10, 2026$/);
    const markers = Array.from(day.querySelectorAll("[data-marker]")).map((m) => m.getAttribute("data-marker"));
    expect(markers).toEqual(["filled", "outlined", "filled", "dashed"]);
  });

  it("All measurements says how two or more marked lines combine, and stays quiet for one", async () => {
    const user = userEvent.setup();
    const deciding = (met: boolean) => [
      { key: "small_manifests", observed: 12, unit: "count", threshold: 20, comparison: ">=", met },
      { key: "manifests_per_snapshot", observed: 61, unit: "count", threshold: 100, comparison: ">", met: false },
    ];
    const record: TableReconciliationApiResponse = {
      ...STARTED,
      operations: [
        ...STARTED.operations.filter((o) => o.operation !== "rewrite_manifests" && o.operation !== "expire_snapshots"),
        op({ operation: "rewrite_manifests", combine: "any", measurements: deciding(false) }),
        op({ operation: "expire_snapshots", combine: "all", measurements: deciding(true) }),
      ],
    };
    stubList([record]);
    renderTab();
    const dialog = await openDrawer(user, /Started Rewrite data files/);
    const open = async (name: string) => {
      const block = within(dialog).getByRole("region", { name });
      await user.click(within(block).getByRole("button", { name: "All measurements" }));
      return block;
    };
    expect(within(await open("Rewrite manifests")).getByText("Starts when any marked line holds")).toBeInTheDocument();
    expect(within(await open("Expire snapshots")).getByText("Starts when every marked line holds")).toBeInTheDocument();
    expect(within(await open("Rewrite data files")).queryByText(/^Starts when/)).not.toBeInTheDocument();
  });

  it("shows No reconciliations yet. when empty", async () => {
    stubList([]);
    renderTab();
    expect(await screen.findByText("No reconciliations yet.")).toBeInTheDocument();
  });

  it("says so when the list cannot be loaded", async () => {
    stubCatalogApi({ "GET /v1/tables/uuid-orders/reconciliations*": () => jsonResponse({ detail: "database down" }, 500) });
    renderTab();
    expect(await screen.findByText("Could not load reconciliations: database down")).toBeInTheDocument();
  });

  it("Show older requests before the oldest record", async () => {
    const user = userEvent.setup();
    const page = Array.from({ length: 50 }, (_, i) => quiet(`rec-p${i}`, new Date(2026, 10, 10, 23, 59 - i).toISOString()));
    const oldest = page.at(-1)!.reconciled_at;
    const older = [{ ...STARTED, reconciled_at: at(9, 8) }];
    const calls = stubCatalogApi({
      "GET /v1/tables/uuid-orders/reconciliations*": () => jsonResponse(calls.length === 1 ? page : older),
    });
    renderTab();

    await user.click(await screen.findByRole("button", { name: "Show older" }));

    await screen.findByRole("button", { name: /Started Rewrite data files/ });
    const params = () => calls.map((call) => new URL(call.path, "http://x").searchParams);
    await waitFor(() => expect(params()).toHaveLength(2));
    expect(params()[0]?.get("before")).toBeNull();
    expect(params()[0]?.get("limit")).toBe("50");
    expect(params()[1]?.get("before")).toBe(oldest);
    expect(screen.queryByRole("button", { name: "Show older" })).not.toBeInTheDocument();
  });
});
