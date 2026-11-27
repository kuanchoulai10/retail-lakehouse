import type { ReactNode } from "react";
import { TooltipProvider } from "@retail-lakehouse/design-system";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { describe, expect, it, vi } from "vitest";
import type { CatalogTableApiResponse, ScannedCatalogApiResponse, TableApiResponse } from "../api/generated/model";
import { getListCatalogTablesQueryKey } from "../api/generated/tables/tables";
import {
  bodyOf,
  callsTo,
  catalogTableFixture,
  catalogTablePropertiesFixture,
  stubCatalogApi,
  type StubHandler,
} from "../test/catalogApiStub";
import {
  effectiveDiscoveryFixture,
  effectiveMaintenanceFixture,
  jsonResponse,
  policyFixture,
  tableFixture,
} from "../test/fixtures";
import { settle, SuspendForever } from "../test/SuspendForever";
import { temporalWorkflowsUrl } from "../lib/temporalWorkflowsUrl";
import { TablePage } from "./TablePage";

const TABLE = "/v1/catalogs/iceberg/namespaces/retail/tables/orders";
const PAGE = "/catalogs/iceberg/namespaces/retail/tables/orders";
const TABS = ["Overview", "Schema", "Properties", "Commits", "Maintenance", "Reconciliations"];

function Location() {
  const location = useLocation();
  return <p data-testid="location">{location.pathname}</p>;
}

function renderAt(path: string, namespacePage: ReactNode = <p>namespace page</p>) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <TooltipProvider>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/catalogs/:catalog/namespaces/:namespace" element={namespacePage} />
            <Route path="/catalogs/:catalog/namespaces/:namespace/tables/:table/:tab?" element={<TablePage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </TooltipProvider>
    </QueryClientProvider>,
  );
  return client;
}

function maintenance(overrides: Partial<TableApiResponse> = {}): TableApiResponse {
  return tableFixture({
    namespace: "retail",
    decided_by: { policy_id: SALES_TABLES_ID, policy_version: 2, rule_position: 1 },
    ...overrides,
  });
}

interface Options {
  table?: CatalogTableApiResponse;
  scanned?: ScannedCatalogApiResponse[];
  maintenanceTable?: () => Response | Promise<Response>;
  extra?: Record<string, StubHandler>;
}

function stubTable({ table = catalogTableFixture(), scanned = [ICEBERG_SCANNED], maintenanceTable, extra = {} }: Options = {}) {
  return stubCatalogApi({
    [`GET ${TABLE}`]: () => jsonResponse(table),
    [`GET ${TABLE}/properties`]: () => jsonResponse(catalogTablePropertiesFixture()),
    [`GET ${TABLE}/schema-versions`]: () => jsonResponse(SCHEMA_VERSIONS),
    [`GET ${TABLE}/schema-versions/0/comparison*`]: () => jsonResponse(SCHEMA_COMPARISON),
    [`GET ${TABLE}/partition-spec-versions`]: () => jsonResponse(SPEC_VERSIONS),
    [`GET ${TABLE}/partition-spec-versions/0/comparison*`]: () => jsonResponse(SPEC_COMPARISON),
    "GET /v1/scanned-catalogs": () => jsonResponse({ catalogs: scanned }),
    "GET /v1/discovery-policies": () => jsonResponse({ policies: [SALES_TABLES] }),
    "GET /v1/tables/uuid-orders": maintenanceTable ?? (() => jsonResponse(maintenance())),
    "GET /v1/tables/uuid-orders/commits*": () => jsonResponse({ items: [], truncated: false }),
    "GET /v1/tables/uuid-orders/metrics/current": () => jsonResponse(CURRENT_METRICS),
    "GET /v1/tables/uuid-orders/metrics*": () => jsonResponse(METRIC_TRENDS),
    "GET /v1/tables/uuid-orders/table-maintenance-runs": () => jsonResponse([]),
    ...extra,
  });
}

const SCHEMA_VERSIONS = {
  current_schema_id: 0,
  versions: [{ schema_id: 0, previous_schema_id: null, current: true, column_count: 3, changes: null }],
};

function schemaField(id: number, path: string[], type: string, required: boolean) {
  return {
    field_id: id,
    depth: path.length - 1,
    path,
    previous_path: path,
    type,
    previous_type: type,
    required,
    previous_required: required,
    doc: null,
    previous_doc: null,
    changes: [],
  };
}

const SCHEMA_COMPARISON = {
  schema_id: 0,
  base_schema_id: null,
  fields: [
    schemaField(1, ["id"], "long", true),
    schemaField(2, ["placed_at"], "timestamptz", false),
    schemaField(3, ["address"], "struct", false),
    schemaField(4, ["address", "city"], "string", true),
    schemaField(5, ["address", "zip"], "string", false),
  ],
};

const SPEC_VERSIONS = {
  default_spec_id: 0,
  versions: [{ spec_id: 0, previous_spec_id: null, default: true, field_count: 1, changes: null }],
};

const SPEC_COMPARISON = {
  spec_id: 0,
  base_spec_id: null,
  fields: [
    {
      field_id: 1000,
      previous_field_id: 1000,
      name: "placed_at_day",
      previous_name: "placed_at_day",
      transform: "day",
      previous_transform: "day",
      expression: "day(placed_at)",
      previous_expression: "day(placed_at)",
      source_path: ["placed_at"],
      previous_source_path: ["placed_at"],
      changes: [],
    },
  ],
};

const CURRENT_METRICS = {
  observed_at: "2026-11-20T09:58:00Z",
  metrics: {
    data_files: 1174,
    position_delete_files: 0,
    equality_delete_files: 0,
    deletion_vectors: 0,
    data_records: 2180,
    position_delete_records: 0,
    equality_delete_records: 0,
    data_size_bytes: 1_824_310,
    reducible_files: 3,
    snapshots: 2,
    manifests: 2,
    manifests_size_bytes: 16_384,
    manifest_added_entries: 4,
    manifest_existing_entries: 3,
    manifest_deleted_entries: 0,
  },
};

const METRIC_TRENDS = {
  time_range: "6h",
  start: "2026-11-20T04:00:00Z",
  end: "2026-11-20T10:00:00Z",
  step_seconds: 180,
  points: [{ at: "2026-11-20T10:00:00Z", values: CURRENT_METRICS.metrics }],
};

const ICEBERG_SCANNED: ScannedCatalogApiResponse = {
  catalog: "iceberg",
  last_discovered_at: "2026-11-09T08:10:00Z",
  failure: null,
};
const OTHER_SCANNED: ScannedCatalogApiResponse = { ...ICEBERG_SCANNED, catalog: "other" };
const ICEBERG_REFUSED: ScannedCatalogApiResponse = {
  ...ICEBERG_SCANNED,
  failure: {
    reason: "cannot_access",
    detail: "the platform's catalog credential cannot read catalog iceberg",
    failed_at: "2026-11-09T09:10:00Z",
  },
};

// sales-tables decided the table at v2 by its first rule, which the current v3 has moved to second.
const SALES_TABLES_ID = "dp-01m7s6c3tqee0rhg00xry2zqqv";
const ORDERS_RULE = { action: "include", table_name_pattern: "orders*" };
const TEMPORARY_RULE = { action: "exclude", table_name_pattern: "tmp_*" };
const SALES_TABLES = {
  id: SALES_TABLES_ID,
  name: "sales-tables",
  version: 3,
  description: "",
  rules: [TEMPORARY_RULE, ORDERS_RULE],
  attachment_count: 1,
  created_at: "2026-11-02T09:00:00Z",
  updated_at: "2026-11-05T09:00:00Z",
};

const UNMANAGED: [string, Options, string][] = [
  ["catalog-not-scanned", { scanned: [OTHER_SCANNED] }, "no discovery policy in this catalog manages tables"],
  [
    "catalog-cannot-access",
    { scanned: [ICEBERG_REFUSED] },
    "discovery cannot read this catalog with the platform's catalog credential",
  ],
  [
    "not-found",
    { maintenanceTable: () => jsonResponse({ detail: "table uuid-orders not found" }, 404) },
    "discovery has not found this table yet",
  ],
  [
    "undecided",
    { maintenanceTable: () => jsonResponse(maintenance({ status: "undecided", decided_by: null })) },
    "discovery has not decided this table yet",
  ],
  [
    "unmanaged",
    { maintenanceTable: () => jsonResponse(maintenance({ status: "unmanaged" })) },
    "no discovery policy that applies to this table manages it",
  ],
  [
    "dropped",
    { maintenanceTable: () => jsonResponse(maintenance({ status: "dropped" })) },
    "maintenance recorded this table as dropped",
  ],
];

async function openAction(user: ReturnType<typeof userEvent.setup>, label: string) {
  await user.click(await screen.findByRole("button", { name: "Actions" }));
  await user.click(await screen.findByRole("menuitem", { name: label }));
}

function tabNames(): string[] {
  return screen.getAllByRole("tab").map((tab) => tab.textContent ?? "");
}

// These tests type into dialogs, which takes seconds under a loaded parallel run.
describe("TablePage", { timeout: 15_000 }, () => {
  it("every table shows the same tabs, with no settings tab", async () => {
    stubTable();
    renderAt(PAGE);
    await screen.findByText("Maintenance: managed");
    expect(tabNames()).toEqual(TABS);
  });

  it("every table shows the same tabs when maintenance does not manage it", async () => {
    stubTable({ scanned: [] });
    renderAt(PAGE);
    await screen.findByText("Maintenance: not managed");
    expect(tabNames()).toEqual(TABS);
  });

  it("the old settings path shows the overview", async () => {
    stubTable();
    renderAt(`${PAGE}/settings`);
    expect(await screen.findByText("Maintenance: managed")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
  });

  describe.each(UNMANAGED)("unmanaged table (%s)", (_reason, options, message) => {
    it.each(["commits", "maintenance", "reconciliations"])(
      "unmanaged table shows the empty state on commits maintenance and reconciliations: %s",
      async (tab) => {
        stubTable(options);
        renderAt(`${PAGE}/${tab}`);
        expect(await screen.findByText(message)).toBeInTheDocument();
        expect(screen.getByText("Maintenance does not manage this table")).toBeInTheDocument();
        expect(screen.queryByRole("button", { name: "Run maintenance" })).not.toBeInTheDocument();
        expect(screen.queryByRole("button", { name: /Pause|Resume/ })).not.toBeInTheDocument();
      },
    );
  });

  it("overview shows the policies that apply and the dry run below the Table panel, and the header shows neither", async () => {
    const effective = {
      policies: [
        effectiveMaintenanceFixture({ policy_name: "scratch", version: 2, dry_run: true }),
        effectiveDiscoveryFixture({ target: { type: "catalog", path: ["iceberg"], table_uuid: null } }),
      ],
    };
    const calls = stubTable({ extra: { "GET /v1/tables/uuid-orders/effective-policies": () => jsonResponse(effective) } });
    renderAt(PAGE);
    const panel = within(await screen.findByRole("region", { name: "Policies" }));
    expect(await panel.findByText("Platform default")).toBeInTheDocument();
    expect(panel.getByText("From catalog", { exact: false })).toBeInTheDocument();
    expect(panel.getByRole("link", { name: "scratch v2" })).toBeInTheDocument();
    expect(panel.getByText("Dry run")).toBeInTheDocument();
    const table = screen.getByRole("region", { name: "Table" });
    expect(table.compareDocumentPosition(screen.getByRole("region", { name: "Policies" }))).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    );
    const heading = screen.getByRole("heading", { level: 1, name: "orders" });
    const header = within(heading.closest("header") as HTMLElement);
    expect(header.queryByText("Dry run")).not.toBeInTheDocument();
    expect(header.queryByText(/Policy:/)).not.toBeInTheDocument();
    expect(header.queryByText(/Rule:/)).not.toBeInTheDocument();
    expect(header.queryByText("Managed")).not.toBeInTheDocument();
    expect(callsTo(calls, "GET", "/v1/tables/uuid-orders/effective-policies")).toHaveLength(1);
  });

  it("the old policy path lands on the overview url, with the policy block and no 404", async () => {
    stubTable();
    renderAt(`${PAGE}/policy`);
    expect(await screen.findByRole("region", { name: "Policies" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("location")).toHaveTextContent(`${PAGE}/overview`);
    expect(screen.queryByText(/not found/i)).not.toBeInTheDocument();
  });

  it("overview asks by location for a table maintenance has no record of, and attaches to it", async () => {
    const byName = "/v1/effective-policies?catalog=iceberg&namespace=retail&table=orders";
    const calls = stubTable({
      scanned: [OTHER_SCANNED],
      maintenanceTable: () => jsonResponse({ detail: "table uuid-orders not found" }, 404),
      extra: {
        [`GET ${byName}`]: () =>
          jsonResponse({
            policies: [effectiveMaintenanceFixture({ policy_name: "default", version: 1 }), effectiveDiscoveryFixture()],
          }),
        "GET /v1/maintenance-policies": () =>
          jsonResponse({ policies: [policyFixture({ name: "default" }), policyFixture({ name: "scratch" })] }),
        "PUT /v1/maintenance-policies/scratch/attachments": () =>
          jsonResponse({
            policy_id: "pol-01m7sd16b1ef2vww335cwcg9k8",
            policy_name: "scratch",
            target: { type: "table", path: ["iceberg", "retail", "orders"], table_uuid: "uuid-orders" },
          }),
      },
    });
    renderAt(PAGE);
    expect(await screen.findAllByText("Platform default")).toHaveLength(1);
    expect(screen.getByText("No discovery policy applies")).toBeInTheDocument();
    expect(screen.getByText("no discovery policy in this catalog manages tables")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Attach policy for maintenance" }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("combobox", { name: "Policy" }));
    await userEvent.click(await screen.findByRole("option", { name: "scratch" }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Attach" }));
    await waitFor(() => expect(callsTo(calls, "GET", byName)).toHaveLength(2));
    expect(bodyOf(calls, "PUT", "/v1/maintenance-policies/scratch/attachments")).toEqual({
      target: { type: "table", path: ["iceberg", "retail", "orders"] },
    });
    expect(callsTo(calls, "GET", "/v1/tables/uuid-orders/effective-policies")).toHaveLength(0);
  });

  it("reads the record again after an attach to a table discovery has not found, which is then undecided", async () => {
    const byName = "/v1/effective-policies?catalog=iceberg&namespace=retail&table=orders";
    const byUuid = "/v1/tables/uuid-orders/effective-policies";
    const attachedHere = { type: "table", path: ["iceberg", "retail", "orders"], table_uuid: "uuid-orders" };
    let recorded = false;
    const calls = stubTable({
      maintenanceTable: () =>
        recorded
          ? jsonResponse(maintenance({ status: "undecided", decided_by: null }))
          : jsonResponse({ detail: "table uuid-orders not found" }, 404),
      extra: {
        [`GET ${byName}`]: () =>
          jsonResponse({ policies: [effectiveMaintenanceFixture({ policy_name: "default", version: 1 }), effectiveDiscoveryFixture()] }),
        [`GET ${byUuid}`]: () =>
          jsonResponse({
            policies: [
              effectiveMaintenanceFixture({ policy_name: "default", version: 1 }),
              effectiveDiscoveryFixture({ target: attachedHere }),
            ],
          }),
        "PUT /v1/discovery-policies/sales-tables/attachments": () => {
          recorded = true;
          return jsonResponse({ policy_id: SALES_TABLES_ID, policy_name: "sales-tables", target: attachedHere });
        },
      },
    });
    renderAt(PAGE);
    expect(await screen.findByText("discovery has not found this table yet")).toBeInTheDocument();
    await userEvent.click(await screen.findByRole("button", { name: "Attach policy for discovery" }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("combobox", { name: "Policy" }));
    await userEvent.click(await screen.findByRole("option", { name: "sales-tables" }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Attach" }));

    expect(await screen.findByText("discovery has not decided this table yet")).toBeInTheDocument();
    expect(await screen.findByText("Attached here")).toBeInTheDocument();
    expect(callsTo(calls, "GET", byUuid)).toHaveLength(1);
    expect(screen.queryByText(/No discovery policy applies/)).not.toBeInTheDocument();
  });

  it("never asks maintenance about a catalog discovery does not scan for the commits tab", async () => {
    const calls = stubTable({ scanned: [] });
    renderAt(`${PAGE}/commits`);
    await screen.findByText("no discovery policy in this catalog manages tables");
    expect(callsTo(calls, "GET", "/v1/tables/uuid-orders/commits")).toHaveLength(0);
  });

  it("managed marker on overview", async () => {
    stubTable();
    renderAt(PAGE);
    const summary = await screen.findByRole("region", { name: "Table" });
    expect(await within(summary).findByText("Maintenance: managed")).toBeInTheDocument();
    expect(within(summary).getByText("s3://warehouse/retail/orders")).toBeInTheDocument();
    expect(within(summary).getByText("9007199254740993")).toBeInTheDocument();
  });

  it("overview shows one loading state while maintenance's answer is pending", async () => {
    stubTable({ maintenanceTable: () => new Promise<Response>(() => {}) });
    renderAt(PAGE);
    const summary = await screen.findByRole("region", { name: "Table" });
    expect(await within(summary).findByText("Maintenance: checking…")).toBeInTheDocument();
    await settle();
    expect(screen.getAllByRole("status")).toHaveLength(1);
    expect(screen.queryByText("Loading maintenance…")).not.toBeInTheDocument();
  });

  it("overview shows the metrics dashboard above the Table panel, and no commits or runs", async () => {
    const calls = stubTable();
    renderAt(PAGE);
    const summary = await screen.findByRole("region", { name: "Table" });
    await within(summary).findByText("Maintenance: managed");
    const files = await screen.findByRole("region", { name: "Files" });
    expect(files.compareDocumentPosition(summary)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    expect(await within(await screen.findByRole("group", { name: "Data files" })).findByText("1,174")).toBeInTheDocument();
    for (const label of ["Rows", "Data files", "Size"]) {
      expect(within(summary).queryByText(label)).not.toBeInTheDocument();
    }
    await settle();
    for (const name of ["Recent commits", "Last maintenance run"]) {
      expect(screen.queryByRole("region", { name })).not.toBeInTheDocument();
    }
    expect(screen.queryByText("No maintenance runs yet.")).not.toBeInTheDocument();
    for (const path of ["commits*", "table-maintenance-runs"]) {
      expect(calls.filter((call) => call.path.startsWith(`/v1/tables/uuid-orders/${path.replace("*", "")}`))).toHaveLength(0);
    }
    expect(callsTo(calls, "GET", "/v1/tables/uuid-orders/metrics/current")).toHaveLength(1);
    expect(callsTo(calls, "GET", "/v1/tables/uuid-orders/metrics?range=6h")).toHaveLength(1);
    expect(screen.queryByText("Maintenance does not manage this table")).not.toBeInTheDocument();
  });

  it("overview shows no metrics dashboard for a table maintenance does not manage", async () => {
    const calls = stubTable({ scanned: [] });
    renderAt(PAGE);
    await screen.findByText("Maintenance: not managed");
    await settle();
    expect(screen.queryByRole("region", { name: "Files" })).not.toBeInTheDocument();
    expect(calls.filter((call) => call.path.startsWith("/v1/tables/uuid-orders/metrics"))).toHaveLength(0);
  });

  it("overview names the discovery policy and version that decided a managed table, and its rule's position", async () => {
    const calls = stubTable();
    renderAt(PAGE);
    const summary = await screen.findByRole("region", { name: "Table" });
    const link = await within(summary).findByRole("link", { name: "sales-tables v2" });
    expect(link).toHaveAttribute("href", "/discovery-policies/sales-tables/versions/2");
    expect(summary).toHaveTextContent("Maintenance: managed · discovery policy sales-tables v2 · rule 1");
    // The position comes with the table; no version is read to find it.
    expect(calls.filter((call) => call.path.includes("/versions/"))).toHaveLength(0);
  });

  it("overview says no rule matched for a table the applying policy left unmanaged", async () => {
    stubTable({
      maintenanceTable: () =>
        jsonResponse(
          maintenance({
            status: "unmanaged",
            decided_by: { policy_id: SALES_TABLES_ID, policy_version: 2, rule_position: null },
          }),
        ),
    });
    renderAt(PAGE);
    const summary = await screen.findByRole("region", { name: "Table" });
    await within(summary).findByRole("link", { name: "sales-tables v2" });
    expect(summary).toHaveTextContent("Maintenance: not managed · discovery policy sales-tables v2 · no rule matched");
    expect(summary).not.toHaveTextContent("· rule ");
  });

  it("overview names the exclude rule that left a table unmanaged", async () => {
    stubTable({
      maintenanceTable: () =>
        jsonResponse(
          maintenance({
            status: "unmanaged",
            decided_by: { policy_id: SALES_TABLES_ID, policy_version: 3, rule_position: 2 },
          }),
        ),
    });
    renderAt(PAGE);
    const summary = await screen.findByRole("region", { name: "Table" });
    await within(summary).findByRole("link", { name: "sales-tables v3" });
    expect(summary).toHaveTextContent("Maintenance: not managed · discovery policy sales-tables v3 · rule 2");
  });

  it("overview says no discovery policy applies, without asking for the policies", async () => {
    const calls = stubTable({
      maintenanceTable: () => jsonResponse(maintenance({ status: "unmanaged", decided_by: null })),
    });
    renderAt(PAGE);
    const summary = await screen.findByRole("region", { name: "Table" });
    await waitFor(() => expect(summary).toHaveTextContent("Maintenance: not managed · No discovery policy applies"));
    await settle();
    expect(callsTo(calls, "GET", "/v1/discovery-policies")).toHaveLength(0);
  });

  it("overview shows a deleted policy's id, with no link, and still its rule", async () => {
    stubTable({ extra: { "GET /v1/discovery-policies": () => jsonResponse({ policies: [] }) } });
    renderAt(PAGE);
    const summary = await screen.findByRole("region", { name: "Table" });
    const id = await within(summary).findByText(SALES_TABLES_ID);
    expect(id).toHaveClass("font-mono");
    expect(summary).toHaveTextContent(`Maintenance: managed · discovery policy ${SALES_TABLES_ID} v2 · rule 1`);
    expect(within(summary).queryByRole("link", { name: /v2/ })).not.toBeInTheDocument();
  });

  it("overview shows the table's priority and saves a new one, then reads the record again", async () => {
    const user = userEvent.setup();
    let record = maintenance({ priority: "P3" });
    const calls = stubTable({
      maintenanceTable: () => jsonResponse(record),
      extra: {
        "PUT /v1/tables/uuid-orders/priority": (body) => {
          record = maintenance({ priority: (body as { priority: string }).priority });
          return jsonResponse(record);
        },
      },
    });
    renderAt(PAGE);
    const summary = await screen.findByRole("region", { name: "Table" });
    const select = await within(summary).findByRole("combobox", { name: "Priority" });
    expect(select).toHaveTextContent("P3 · default");
    await user.click(select);
    await user.click(await screen.findByRole("option", { name: "P0 · urgent" }));
    await waitFor(() => expect(bodyOf(calls, "PUT", "/v1/tables/uuid-orders/priority")).toEqual({ priority: "P0" }));
    await waitFor(() => expect(within(summary).getByRole("combobox", { name: "Priority" })).toHaveTextContent("P0 · urgent"));
    expect(callsTo(calls, "GET", "/v1/tables/uuid-orders").length).toBeGreaterThan(1);
  });

  it("overview shows a dropped table's priority read-only", async () => {
    stubTable({ maintenanceTable: () => jsonResponse(maintenance({ status: "dropped", priority: "P1" })) });
    renderAt(PAGE);
    const summary = await screen.findByRole("region", { name: "Table" });
    const select = await within(summary).findByRole("combobox", { name: "Priority" });
    expect(select).toBeDisabled();
    expect(select).toHaveTextContent("P1");
  });

  it("overview has no priority for a table maintenance has no record of", async () => {
    stubTable({ maintenanceTable: () => jsonResponse({ detail: "table uuid-orders not found" }, 404) });
    renderAt(PAGE);
    await screen.findByText("Maintenance: not managed");
    await settle();
    expect(screen.queryByRole("combobox", { name: "Priority" })).not.toBeInTheDocument();
  });

  it("overview says nothing of a discovery policy for a dropped table", async () => {
    const calls = stubTable({ maintenanceTable: () => jsonResponse(maintenance({ status: "dropped" })) });
    renderAt(PAGE);
    await screen.findByText("Maintenance: not managed");
    await settle();
    expect(screen.getByRole("region", { name: "Table" })).not.toHaveTextContent("discovery policy");
    expect(callsTo(calls, "GET", "/v1/discovery-policies")).toHaveLength(0);
  });

  it("names a scanned catalog discovery cannot read on the overview, and links to the discovery policies", async () => {
    stubTable({ scanned: [ICEBERG_REFUSED] });
    renderAt(PAGE);
    expect(
      await screen.findByText("discovery cannot read this catalog with the platform's catalog credential"),
    ).toBeInTheDocument();
    expect(screen.getByText("Maintenance: not managed")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Discovery policies" })).toHaveAttribute("href", "/discovery-policies");
  });

  it("maintenance tab links to the table's running workflows in Temporal", async () => {
    stubTable();
    renderAt(`${PAGE}/maintenance`);
    const link = await screen.findByRole("link", { name: "Running workflows in Temporal" });
    expect(link).toHaveAttribute("href", temporalWorkflowsUrl("uuid-orders"));
  });

  it("shows the not managed marker and the empty state on overview", async () => {
    stubTable({ maintenanceTable: () => jsonResponse(maintenance({ status: "unmanaged" })) });
    renderAt(PAGE);
    const summary = await screen.findByRole("region", { name: "Table" });
    expect(await within(summary).findByText("Maintenance: not managed")).toBeInTheDocument();
    expect(screen.getByText("no discovery policy that applies to this table manages it")).toBeInTheDocument();
  });

  it("shows the header numbers from the catalog summary", async () => {
    stubTable();
    renderAt(PAGE);
    const heading = await screen.findByRole("heading", { level: 1, name: "orders" });
    const header = within(heading.closest("header") as HTMLElement);
    expect(header.getByText("1,204,331 rows")).toBeInTheDocument();
    expect(header.getByText("100 data files")).toBeInTheDocument();
    expect(header.getByText("320.0 MB")).toBeInTheDocument();
    expect(header.getByText("2 snapshots")).toBeInTheDocument();
    const crumbs = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(within(crumbs).getByRole("link", { name: "retail" })).toHaveAttribute(
      "href",
      "/catalogs/iceberg/namespaces/retail",
    );
  });

  it("shows run maintenance and no pause or resume when the table is managed", async () => {
    stubTable();
    renderAt(PAGE);
    expect(await screen.findByRole("button", { name: "Run maintenance" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: /Pause|Resume/ })).not.toBeInTheDocument();
  });

  it("shows the polaris tabs when maintenance fails to answer", async () => {
    stubTable({ maintenanceTable: () => jsonResponse({ detail: "database down" }, 500) });
    renderAt(`${PAGE}/properties`);
    expect(await screen.findByText("write.format.default")).toBeInTheDocument();
  });

  it("shows the maintenance error on a maintenance tab", async () => {
    stubTable({ maintenanceTable: () => jsonResponse({ detail: "database down" }, 500) });
    renderAt(`${PAGE}/commits`);
    expect(await screen.findByText(/Could not load maintenance: database down/)).toBeInTheDocument();
  });

  it("shows the schema with partition spec sort order and spark ddl", async () => {
    stubTable();
    renderAt(`${PAGE}/schema`);
    const fields = await screen.findByRole("region", { name: "Schema" });
    expect(await within(fields).findByText("Current")).toBeInTheDocument();
    expect(await within(fields).findByText("address.zip")).toBeInTheDocument();
    expect(within(fields).getByText("struct · optional")).toBeInTheDocument();
    const spec = screen.getByRole("region", { name: "Partition spec" });
    expect(await within(spec).findByText("Default")).toBeInTheDocument();
    expect(await within(spec).findByText("day(placed_at)")).toBeInTheDocument();
    const order = screen.getByRole("region", { name: "Sort order" });
    expect(within(order).getByText("nulls-first")).toBeInTheDocument();
    const ddl = screen.getByRole("region", { name: "DDL (Spark SQL)" });
    expect(ddl).toHaveTextContent("CREATE TABLE `iceberg`.`retail`.`orders`");
    expect(ddl).toHaveTextContent("`address` STRUCT<`city`: STRING NOT NULL, `zip`: STRING>");
  });

  it("has no snapshots tab: its old url opens the overview", async () => {
    stubTable();
    renderAt(`${PAGE}/snapshots`);
    await screen.findByText("Maintenance: managed");
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByRole("tab", { name: "Snapshots" })).not.toBeInTheDocument();
  });

  it("rename navigates to the new url", async () => {
    const user = userEvent.setup();
    const renamed = catalogTableFixture({ namespace: ["retail", "eu"], name: "orders_v2" });
    const calls = stubTable({
      extra: {
        [`POST ${TABLE}/rename`]: () =>
          jsonResponse({ catalog: "iceberg", namespace: ["retail", "eu"], name: "orders_v2" }),
        "GET /v1/catalogs/iceberg/namespaces/retail%1Feu/tables/orders_v2": () => jsonResponse(renamed),
      },
    });
    renderAt(`${PAGE}/schema`);
    await openAction(user, "Rename");
    const dialog = await screen.findByRole("dialog", { name: "Rename table" });
    await user.click(within(dialog).getByRole("button", { name: "Add level" }));
    await user.type(within(dialog).getByLabelText("Namespace level 2"), "eu");
    const name = within(dialog).getByLabelText("Name");
    await user.clear(name);
    await user.type(name, "orders_v2");
    await user.click(within(dialog).getByRole("button", { name: "Rename" }));

    expect(bodyOf(calls, "POST", `${TABLE}/rename`)).toEqual({
      target_namespace: ["retail", "eu"],
      target_name: "orders_v2",
    });
    expect(await screen.findByRole("heading", { level: 1, name: "orders_v2" })).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent(
      "/catalogs/iceberg/namespaces/retail%1Feu/tables/orders_v2/schema",
    );
    expect(callsTo(calls, "GET", TABLE)).toHaveLength(1);
  });

  it("links a commit of a table in a nested namespace to its schema version on the Schema tab", async () => {
    const nested = "/v1/catalogs/iceberg/namespaces/retail%1Feu/tables/orders";
    stubTable({
      extra: {
        [`GET ${nested}`]: () => jsonResponse(catalogTableFixture({ namespace: ["retail", "eu"] })),
        "GET /v1/tables/uuid-orders": () => jsonResponse(maintenance({ namespace: "retail.eu" })),
        "GET /v1/tables/uuid-orders/commits*": () =>
          jsonResponse({
            items: [
              {
                snapshot_id: "1111111222",
                parent_id: null,
                committed_at: "2026-10-31T12:00:00Z",
                operation: "append",
                writer: "kafka_connect",
                schema_id: 3,
                added_records: 1,
                deleted_records: 0,
                added_data_files: 1,
                deleted_data_files: 0,
                added_delete_files: 0,
                removed_delete_files: 0,
                summary: {},
              },
            ],
            truncated: false,
          }),
      },
    });
    renderAt("/catalogs/iceberg/namespaces/retail%1Feu/tables/orders/commits");
    const link = await screen.findByRole("link", { name: "Schema v3" });
    const href = link.getAttribute("href") ?? "";
    expect(href).toContain("%1F");
    expect(href).toContain("/schema?schema=");
    expect(href).toBe("/catalogs/iceberg/namespaces/retail%1Feu/tables/orders/schema?schema=3");
  });

  it("the actions menu holds rename and delete only; properties are edited in the Properties tab", async () => {
    const user = userEvent.setup();
    stubTable();
    renderAt(PAGE);
    await user.click(await screen.findByRole("button", { name: "Actions" }));
    const items = await screen.findAllByRole("menuitem");
    expect(items.map((item) => item.textContent)).toEqual(["Rename", "Delete"]);
  });

  it("edit properties sends the loaded uuid and only the changes", async () => {
    const user = userEvent.setup();
    const calls = stubTable({
      extra: { [`PUT ${TABLE}/properties`]: () => jsonResponse(catalogTableFixture()) },
    });
    renderAt(`${PAGE}/properties`);
    await user.click(await screen.findByRole("button", { name: "Edit properties" }));
    const dialog = await screen.findByRole("dialog", { name: "Edit properties" });
    await user.click(within(dialog).getByRole("button", { name: "Remove owner" }));
    await user.click(within(dialog).getByRole("button", { name: "Save" }));
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(bodyOf(calls, "PUT", `${TABLE}/properties`)).toEqual({
      expected_uuid: "uuid-orders",
      updates: {},
      removals: ["owner"],
    });
  });

  it("properties conflict shows reload message", async () => {
    const user = userEvent.setup();
    stubTable({
      extra: {
        [`PUT ${TABLE}/properties`]: () =>
          jsonResponse({ detail: "table iceberg.retail.orders was replaced" }, 409),
      },
    });
    renderAt(`${PAGE}/properties`);
    await user.click(await screen.findByRole("button", { name: "Edit properties" }));
    const dialog = await screen.findByRole("dialog", { name: "Edit properties" });
    await user.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "This table changed since you loaded it, reload and try again.",
    );
    expect(within(dialog).getByRole("button", { name: "Reload" })).toBeInTheDocument();
  });

  it("delete goes to the namespace page", async () => {
    const user = userEvent.setup();
    const calls = stubTable({ extra: { [`DELETE ${TABLE}`]: () => new Response(null, { status: 204 }) } });
    renderAt(PAGE);
    await openAction(user, "Delete");
    const dialog = await screen.findByRole("alertdialog", { name: "Delete table" });
    expect(dialog).toHaveTextContent("iceberg / retail / orders");
    await user.type(within(dialog).getByLabelText(/Type orders to confirm/), "orders");
    await user.click(within(dialog).getByRole("button", { name: "Delete" }));
    expect(await screen.findByText("namespace page")).toBeInTheDocument();
    expect(callsTo(calls, "DELETE", TABLE)).toHaveLength(1);
    expect(callsTo(calls, "GET", TABLE)).toHaveLength(1);
  });

  it("never refetches the deleted table while the navigation is still pending", async () => {
    const user = userEvent.setup();
    const calls = stubTable({ extra: { [`DELETE ${TABLE}`]: () => new Response(null, { status: 204 }) } });
    renderAt(PAGE, <SuspendForever />);
    await openAction(user, "Delete");
    const dialog = await screen.findByRole("alertdialog", { name: "Delete table" });
    await user.type(within(dialog).getByLabelText(/Type orders to confirm/), "orders");
    await user.click(within(dialog).getByRole("button", { name: "Delete" }));
    await vi.waitFor(() => expect(callsTo(calls, "DELETE", TABLE)).toHaveLength(1));
    await settle();
    expect(callsTo(calls, "GET", TABLE)).toHaveLength(1);
  });

  it.each(["nonsense", "candidates"])("falls back to Overview for an unknown tab segment: %s", async (segment) => {
    stubTable();
    renderAt(`${PAGE}/${segment}`);
    await screen.findByRole("region", { name: "Table" });
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
  });

  it("selects the tab named in the URL", async () => {
    stubTable();
    renderAt(`${PAGE}/properties`);
    expect(await screen.findByText("write.format.default")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Properties" })).toHaveAttribute("aria-selected", "true");
  });

  it("navigates to the commits route when the Commits tab is activated", async () => {
    const user = userEvent.setup();
    stubTable();
    renderAt(`${PAGE}/properties`);
    await screen.findByText("write.format.default");
    await user.click(screen.getByRole("tab", { name: "Commits" }));
    expect(await screen.findByText("No commits.")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Commits" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("location")).toHaveTextContent(`${PAGE}/commits`);
  });

  it("does not switch the page on a modified mousedown", async () => {
    stubTable();
    renderAt(`${PAGE}/properties`);
    await screen.findByText("write.format.default");
    fireEvent.mouseDown(screen.getByRole("tab", { name: "Commits" }), { button: 0, metaKey: true });
    expect(screen.getByRole("tab", { name: "Properties" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("location")).toHaveTextContent(`${PAGE}/properties`);
  });

  it("navigates when a tab is activated with the keyboard", async () => {
    const user = userEvent.setup();
    stubTable();
    renderAt(`${PAGE}/properties`);
    await screen.findByText("write.format.default");
    screen.getByRole("tab", { name: "Properties" }).focus();
    await user.keyboard("{ArrowRight}{ArrowRight}");
    expect(await screen.findByText("No maintenance runs yet.")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Maintenance" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("location")).toHaveTextContent(`${PAGE}/maintenance`);
  });

  it("missing table shows renamed-or-dropped state", async () => {
    stubTable({
      extra: { [`GET ${TABLE}`]: () => jsonResponse({ detail: "Table does not exist: retail.orders" }, 404) },
    });
    renderAt(`${PAGE}/commits`);
    expect(await screen.findByText(/may have been renamed or dropped/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Go to iceberg / retail" })).toHaveAttribute(
      "href",
      "/catalogs/iceberg/namespaces/retail",
    );
  });

  it("shows other catalog errors with their message", async () => {
    stubTable({ extra: { [`GET ${TABLE}`]: () => jsonResponse({ detail: "polaris unreachable" }, 502) } });
    renderAt(PAGE);
    expect(await screen.findByText(/Could not load table: polaris unreachable/)).toBeInTheDocument();
  });

  it("refetches the table when a properties save fails", async () => {
    const user = userEvent.setup();
    const calls = stubTable({
      extra: { [`PUT ${TABLE}/properties`]: () => jsonResponse({ detail: "Polaris is unreachable" }, 502) },
    });
    renderAt(`${PAGE}/properties`);
    await user.click(await screen.findByRole("button", { name: "Edit properties" }));
    const dialog = await screen.findByRole("dialog", { name: "Edit properties" });
    await user.click(within(dialog).getByRole("button", { name: "Remove owner" }));
    await user.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Polaris is unreachable");
    await vi.waitFor(() => expect(callsTo(calls, "GET", TABLE).length).toBeGreaterThan(1));
  });

  it("refetches the namespace's tables when a rename fails", async () => {
    const user = userEvent.setup();
    stubTable({
      extra: { [`POST ${TABLE}/rename`]: () => jsonResponse({ detail: "Polaris is unreachable" }, 502) },
    });
    const client = renderAt(PAGE);
    const invalidate = vi.spyOn(client, "invalidateQueries");
    await openAction(user, "Rename");
    const dialog = await screen.findByRole("dialog", { name: "Rename table" });
    const name = within(dialog).getByLabelText("Name");
    await user.clear(name);
    await user.type(name, "orders_v2");
    await user.click(within(dialog).getByRole("button", { name: "Rename" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Polaris is unreachable");
    await vi.waitFor(() =>
      expect(invalidate).toHaveBeenCalledWith({ queryKey: getListCatalogTablesQueryKey("iceberg", "retail") }),
    );
  });
});
