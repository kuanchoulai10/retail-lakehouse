import { QueryClient, QueryClientProvider, type QueryKey } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import {
  getListScannedCatalogsQueryKey,
  getListTableDiscoveryPoliciesQueryKey,
  getListTableDiscoveryPolicyAttachmentsQueryKey,
} from "../api/generated/discovery-policies/discovery-policies";
import {
  getListTableMaintenancePoliciesQueryKey,
  getListTableMaintenancePolicyAttachmentsQueryKey,
} from "../api/generated/maintenance-policies/maintenance-policies";
import type {
  DiscoveryEffectivePolicyApiResponse,
  MaintenanceEffectivePolicyApiResponse,
  PolicyTargetApiResponse,
} from "../api/generated/model";
import type { PolicyScope } from "../lib/policyScope";
import { bodyOf, callsTo, stubCatalogApi, type StubbedCall, type StubHandler } from "../test/catalogApiStub";
import {
  effectiveDiscoveryFixture,
  effectiveMaintenanceFixture,
  jsonResponse,
  NIGHTLY_POLICY_ID,
  policyFixture,
  SCRATCH_POLICY_ID,
} from "../test/fixtures";
import { EffectivePoliciesPanel } from "./EffectivePoliciesPanel";

const TABLE_SCOPE: PolicyScope = {
  type: "table",
  catalog: "iceberg",
  namespace: ["retail"],
  table: "orders",
  tableUuid: "uuid-orders",
  recorded: true,
};
const UNRECORDED_TABLE_SCOPE: PolicyScope = { ...TABLE_SCOPE, recorded: false };
const NAMESPACE_SCOPE: PolicyScope = { type: "namespace", catalog: "iceberg", namespace: ["retail"] };
const SUB_NAMESPACE_SCOPE: PolicyScope = { type: "namespace", catalog: "iceberg", namespace: ["retail", "eu"] };

const TABLE_EFFECTIVE = "/v1/tables/uuid-orders/effective-policies";
const UNRECORDED_TABLE_EFFECTIVE = "/v1/effective-policies?catalog=iceberg&namespace=retail&table=orders";
const NAMESPACE_EFFECTIVE = "/v1/effective-policies?catalog=iceberg&namespace=retail";
const SUB_NAMESPACE_EFFECTIVE = "/v1/effective-policies?catalog=iceberg&namespace=retail.eu";

const AT_CATALOG: PolicyTargetApiResponse = { type: "catalog", path: ["iceberg"], table_uuid: null };
const AT_RETAIL: PolicyTargetApiResponse = { type: "namespace", path: ["iceberg", "retail"], table_uuid: null };
const AT_ORDERS: PolicyTargetApiResponse = { type: "table", path: ["iceberg", "retail", "orders"], table_uuid: "uuid-orders" };

const maintenance = (target: PolicyTargetApiResponse | null, overrides: Partial<MaintenanceEffectivePolicyApiResponse> = {}) =>
  effectiveMaintenanceFixture({ ...overrides, target });
const discovery = (target: PolicyTargetApiResponse | null, overrides: Partial<DiscoveryEffectivePolicyApiResponse> = {}) =>
  effectiveDiscoveryFixture({ ...overrides, target });

function effective(...policies: (MaintenanceEffectivePolicyApiResponse | DiscoveryEffectivePolicyApiResponse)[]) {
  return () => jsonResponse({ policies });
}

const MAINTENANCE_POLICIES = [
  policyFixture({ name: "default" }),
  policyFixture({ id: NIGHTLY_POLICY_ID, name: "nightly", version: 4 }),
  policyFixture({ id: SCRATCH_POLICY_ID, name: "scratch" }),
];
const DISCOVERY_POLICIES = [
  { id: "dp-00000000000000000000000000", name: "default", is_default: true },
  { id: "dp-01m7s6c3tqee0rhg00xry2zqqv", name: "sales-tables", is_default: false },
  { id: "dp-01m7s6c3tqee0rhg00xry2zqqw", name: "core-tables", is_default: false },
];

function stubApi(routes: Record<string, StubHandler>) {
  return stubCatalogApi({
    "GET /v1/maintenance-policies": () => jsonResponse({ policies: MAINTENANCE_POLICIES }),
    "GET /v1/discovery-policies": () => jsonResponse({ policies: DISCOVERY_POLICIES }),
    ...routes,
  });
}

function renderPanel(scope: PolicyScope) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <EffectivePoliciesPanel scope={scope} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return client;
}

// Seeds queries the panel does not show, so a test can see which ones a write marks stale.
function seed(client: QueryClient, keys: Record<string, QueryKey>): () => string[] {
  for (const key of Object.values(keys)) client.setQueryData(key, {});
  return () =>
    Object.entries(keys)
      .filter(([, key]) => client.getQueryState(key)?.isInvalidated)
      .map(([name]) => name);
}

// Whether the policy list the attach dialog read was refetched or marked stale after the write.
function listRefreshed(client: QueryClient, calls: StubbedCall[], write: string, list: QueryKey): boolean {
  const at = calls.findIndex((call) => `${call.method} ${call.path}` === write);
  const readAgain = calls.slice(at + 1).some((call) => call.method === "GET" && call.path === list[0]);
  return at >= 0 && (readAgain || client.getQueryState(list)?.isInvalidated === true);
}

// The text a sighted user reads on a button, without what only a screen reader hears.
function visibleText(element: HTMLElement): string {
  const copy = element.cloneNode(true) as HTMLElement;
  for (const hidden of copy.querySelectorAll(".sr-only")) hidden.remove();
  return copy.textContent?.replace(/\s+/g, " ").trim() ?? "";
}

async function rows(): Promise<HTMLElement[]> {
  const panel = await screen.findByRole("region", { name: "Policies" });
  return within(panel).findAllByRole("listitem");
}

async function pickPolicy(dialog: HTMLElement, name: string) {
  await userEvent.click(await within(dialog).findByRole("combobox", { name: "Policy" }));
  await userEvent.click(await screen.findByRole("option", { name }));
}

describe("EffectivePoliciesPanel", { timeout: 15_000 }, () => {
  it("shows one row per kind in the API's order, each with its policy and the level it comes from", async () => {
    stubApi({ [`GET ${TABLE_EFFECTIVE}`]: effective(maintenance(AT_RETAIL), discovery(AT_CATALOG)) });
    renderPanel(TABLE_SCOPE);
    const [first, second] = await rows();
    const maintenanceRow = within(first!);
    expect(maintenanceRow.getByText("Maintenance")).toBeInTheDocument();
    expect(maintenanceRow.getByRole("link", { name: "nightly v4" })).toHaveAttribute("href", "/policies/nightly/versions/4");
    expect(first).toHaveTextContent("From namespace iceberg.retail");
    expect(maintenanceRow.getByRole("link", { name: "iceberg.retail" })).toHaveAttribute(
      "href",
      "/catalogs/iceberg/namespaces/retail",
    );
    const discoveryRow = within(second!);
    expect(discoveryRow.getByText("Discovery")).toBeInTheDocument();
    expect(discoveryRow.getByRole("link", { name: "sales-tables v2" })).toHaveAttribute(
      "href",
      "/discovery-policies/sales-tables/versions/2",
    );
    expect(second).toHaveTextContent("From catalog iceberg");
    expect(screen.queryByText("Dry run")).not.toBeInTheDocument();
  });

  it("says the platform default applies, and marks a maintenance policy in dry run", async () => {
    stubApi({
      [`GET ${NAMESPACE_EFFECTIVE}`]: effective(
        maintenance(null, { policy_name: "default", version: 3, dry_run: true }),
        discovery(null, { policy_name: "default", version: 1 }),
      ),
    });
    renderPanel(NAMESPACE_SCOPE);
    const [first, second] = await rows();
    expect(within(first!).getByText("Platform default")).toBeInTheDocument();
    expect(within(first!).getByText("Dry run")).toBeInTheDocument();
    expect(within(second!).getByText("Platform default")).toBeInTheDocument();
    expect(within(second!).queryByText("Dry run")).not.toBeInTheDocument();
    expect(visibleText(screen.getByRole("button", { name: "Attach policy for maintenance" }))).toBe("Attach policy");
    expect(visibleText(screen.getByRole("button", { name: "Attach policy for discovery" }))).toBe("Attach policy");
    expect(screen.queryByRole("button", { name: /^Detach/ })).not.toBeInTheDocument();
  });

  it("offers Detach only for the kind attached here", async () => {
    stubApi({ [`GET ${NAMESPACE_EFFECTIVE}`]: effective(maintenance(AT_RETAIL), discovery(AT_CATALOG)) });
    renderPanel(NAMESPACE_SCOPE);
    const [first, second] = await rows();
    expect(first).toHaveTextContent("Attached here");
    expect(visibleText(within(first!).getByRole("button", { name: "Detach maintenance policy" }))).toBe("Detach");
    expect(visibleText(within(first!).getByRole("button", { name: "Replace policy for maintenance" }))).toBe("Replace policy");
    expect(within(second!).queryByRole("button", { name: "Detach discovery policy" })).not.toBeInTheDocument();
    expect(within(second!).getByRole("button", { name: "Attach policy for discovery" })).toBeInTheDocument();
  });

  it("does not offer to detach a policy attached to a parent namespace", async () => {
    stubApi({ [`GET ${SUB_NAMESPACE_EFFECTIVE}`]: effective(maintenance(AT_RETAIL), discovery(AT_RETAIL)) });
    renderPanel(SUB_NAMESPACE_SCOPE);
    const [first, second] = await rows();
    expect(first).toHaveTextContent("From namespace iceberg.retail");
    expect(second).toHaveTextContent("From namespace iceberg.retail");
    expect(screen.queryByRole("button", { name: /^Detach/ })).not.toBeInTheDocument();
  });

  it("detaches the discovery policy attached here by its attachment id and refetches what it changed", async () => {
    const calls = stubApi({
      [`GET ${NAMESPACE_EFFECTIVE}`]: effective(maintenance(AT_CATALOG), discovery(AT_RETAIL)),
      "DELETE /v1/discovery-policies/sales-tables/attachments/da-01m7s6c3tqee0rhg00xry2zqqx": () =>
        new Response(null, { status: 204 }),
    });
    const client = renderPanel(NAMESPACE_SCOPE);
    const stale = seed(client, {
      attachments: getListTableDiscoveryPolicyAttachmentsQueryKey("sales-tables"),
      discoveryPolicies: getListTableDiscoveryPoliciesQueryKey(),
      scanned: getListScannedCatalogsQueryKey(),
      maintenancePolicies: getListTableMaintenancePoliciesQueryKey(),
    });
    await userEvent.click(await screen.findByRole("button", { name: "Detach discovery policy" }));
    await waitFor(() => expect(callsTo(calls, "GET", NAMESPACE_EFFECTIVE)).toHaveLength(2));
    expect(
      callsTo(calls, "DELETE", "/v1/discovery-policies/sales-tables/attachments/da-01m7s6c3tqee0rhg00xry2zqqx"),
    ).toHaveLength(1);
    expect(stale()).toEqual(["attachments", "discoveryPolicies", "scanned"]);
  });

  it("detaches the maintenance policy attached to a recorded table by its attachment id and refetches what it changed", async () => {
    const detachUrl = "/v1/maintenance-policies/nightly/attachments/pa-01m7sdb2kq9e4z5r7t8vwx3y6d";
    const calls = stubApi({
      [`GET ${TABLE_EFFECTIVE}`]: effective(
        maintenance(AT_ORDERS, { attachment_id: "pa-01m7sdb2kq9e4z5r7t8vwx3y6d" }),
        discovery(AT_CATALOG),
      ),
      [`DELETE ${detachUrl}`]: () => new Response(null, { status: 204 }),
    });
    const client = renderPanel(TABLE_SCOPE);
    const stale = seed(client, {
      attachments: getListTableMaintenancePolicyAttachmentsQueryKey("nightly"),
      maintenancePolicies: getListTableMaintenancePoliciesQueryKey(),
      discoveryPolicies: getListTableDiscoveryPoliciesQueryKey(),
    });
    await userEvent.click(await screen.findByRole("button", { name: "Detach maintenance policy" }));
    await waitFor(() => expect(callsTo(calls, "GET", TABLE_EFFECTIVE)).toHaveLength(2));
    expect(callsTo(calls, "DELETE", detachUrl)).toHaveLength(1);
    expect(stale()).toEqual(["attachments", "maintenancePolicies"]);
  });

  it("asks by location for a table maintenance has no record of", async () => {
    const calls = stubApi({
      [`GET ${UNRECORDED_TABLE_EFFECTIVE}`]: effective(maintenance(AT_ORDERS), discovery(null)),
    });
    renderPanel(UNRECORDED_TABLE_SCOPE);
    const [first] = await rows();
    expect(first).toHaveTextContent("Attached here");
    expect(callsTo(calls, "GET", TABLE_EFFECTIVE)).toHaveLength(0);
  });

  it("attaches a discovery policy here from the discovery policies, and refetches the scan state and counts", async () => {
    const calls = stubApi({
      [`GET ${NAMESPACE_EFFECTIVE}`]: effective(maintenance(null), discovery(AT_CATALOG, { policy_name: "core-tables" })),
      "PUT /v1/discovery-policies/sales-tables/attachments": () =>
        jsonResponse({
          id: "da-new",
          policy_id: "dp-01m7s6c3tqee0rhg00xry2zqqv",
          policy_name: "sales-tables",
          target: AT_RETAIL,
          attached_at: "2026-11-21T09:00:00Z",
        }),
    });
    const client = renderPanel(NAMESPACE_SCOPE);
    const stale = seed(client, {
      attachments: getListTableDiscoveryPolicyAttachmentsQueryKey("sales-tables"),
      scanned: getListScannedCatalogsQueryKey(),
      maintenancePolicies: getListTableMaintenancePoliciesQueryKey(),
    });
    await userEvent.click(await screen.findByRole("button", { name: "Attach policy for discovery" }));
    const dialog = await screen.findByRole("dialog", { name: "Attach policy" });
    await pickPolicy(dialog, "sales-tables");
    await userEvent.click(within(dialog).getByRole("button", { name: "Attach" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(bodyOf(calls, "PUT", "/v1/discovery-policies/sales-tables/attachments")).toEqual({
      target: { type: "namespace", path: ["iceberg", "retail"] },
    });
    await waitFor(() => expect(callsTo(calls, "GET", NAMESPACE_EFFECTIVE)).toHaveLength(2));
    expect(stale()).toEqual(["attachments", "scanned"]);
    expect(
      listRefreshed(client, calls, "PUT /v1/discovery-policies/sales-tables/attachments", getListTableDiscoveryPoliciesQueryKey()),
    ).toBe(true);
  });

  it("replaces the maintenance policy attached here, leaving it out of the choices", async () => {
    const calls = stubApi({
      [`GET ${NAMESPACE_EFFECTIVE}`]: effective(maintenance(AT_RETAIL), discovery(AT_CATALOG)),
      "PUT /v1/maintenance-policies/scratch/attachments": () =>
        jsonResponse({
          id: "pa-01m7sd16b1ef2vww335cwcg9k8",
          policy_name: "scratch",
          policy_id: SCRATCH_POLICY_ID,
          target: AT_RETAIL,
          attached_at: "2026-11-21T09:00:00Z",
        }),
    });
    const client = renderPanel(NAMESPACE_SCOPE);
    const stale = seed(client, {
      nightly: getListTableMaintenancePolicyAttachmentsQueryKey("nightly"),
      scratch: getListTableMaintenancePolicyAttachmentsQueryKey("scratch"),
      scanned: getListScannedCatalogsQueryKey(),
    });
    await userEvent.click(await screen.findByRole("button", { name: "Replace policy for maintenance" }));
    const dialog = await screen.findByRole("dialog", { name: "Replace policy" });
    await userEvent.click(await within(dialog).findByRole("combobox", { name: "Policy" }));
    expect(await screen.findByRole("option", { name: "scratch" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "nightly" })).not.toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "sales-tables" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("option", { name: "scratch" }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Attach" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(bodyOf(calls, "PUT", "/v1/maintenance-policies/scratch/attachments")).toEqual({
      target: { type: "namespace", path: ["iceberg", "retail"] },
    });
    await waitFor(() => expect(callsTo(calls, "GET", NAMESPACE_EFFECTIVE)).toHaveLength(2));
    expect(stale()).toEqual(["nightly", "scratch"]);
    expect(
      listRefreshed(client, calls, "PUT /v1/maintenance-policies/scratch/attachments", getListTableMaintenancePoliciesQueryKey()),
    ).toBe(true);
  });

  it("shows the API's detail when the read fails, and no rows", async () => {
    stubApi({ [`GET ${NAMESPACE_EFFECTIVE}`]: () => jsonResponse({ detail: "catalog iceberg not found" }, 404) });
    renderPanel(NAMESPACE_SCOPE);
    expect(await screen.findByText(/catalog iceberg not found/)).toBeInTheDocument();
    const panel = screen.getByRole("region", { name: "Policies" });
    expect(within(panel).queryByRole("listitem")).not.toBeInTheDocument();
    expect(within(panel).queryByText("Maintenance")).not.toBeInTheDocument();
    expect(within(panel).queryByText("Discovery")).not.toBeInTheDocument();
  });

  it("shows a refused detach and gives focus back to that Detach", async () => {
    const calls = stubApi({
      [`GET ${NAMESPACE_EFFECTIVE}`]: effective(maintenance(AT_RETAIL), discovery(AT_RETAIL)),
      "DELETE /v1/discovery-policies/sales-tables/attachments/da-01m7s6c3tqee0rhg00xry2zqqx": () =>
        jsonResponse({ detail: "database unavailable" }, 500),
    });
    const user = userEvent.setup();
    renderPanel(NAMESPACE_SCOPE);
    await user.click(await screen.findByRole("button", { name: "Detach discovery policy" }));
    expect(await screen.findByText("Could not detach sales-tables: database unavailable")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Detach discovery policy" })).toHaveFocus());
    expect(callsTo(calls, "GET", NAMESPACE_EFFECTIVE)).toHaveLength(2);
  });

  it("works by keyboard: attach opens and closes, and a detach moves focus to that row's attach", async () => {
    let attached = true;
    stubApi({
      [`GET ${NAMESPACE_EFFECTIVE}`]: () =>
        jsonResponse({ policies: [maintenance(attached ? AT_RETAIL : AT_CATALOG), discovery(AT_CATALOG)] }),
      "DELETE /v1/maintenance-policies/nightly/attachments/pa-01m7sd16b1ef2vww335cwcg9k8": () => {
        attached = false;
        return new Response(null, { status: 204 });
      },
    });
    const user = userEvent.setup();
    renderPanel(NAMESPACE_SCOPE);
    const attachDiscovery = await screen.findByRole("button", { name: "Attach policy for discovery" });
    attachDiscovery.focus();
    await user.keyboard("{Enter}");
    const dialog = await screen.findByRole("dialog", { name: "Attach policy" });
    expect(await within(dialog).findByRole("combobox", { name: "Policy" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await waitFor(() => expect(attachDiscovery).toHaveFocus());

    screen.getByRole("button", { name: "Detach maintenance policy" }).focus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(screen.getByRole("button", { name: "Attach policy for maintenance" })).toHaveFocus());
    expect(screen.queryByRole("button", { name: "Detach maintenance policy" })).not.toBeInTheDocument();
  });
});
