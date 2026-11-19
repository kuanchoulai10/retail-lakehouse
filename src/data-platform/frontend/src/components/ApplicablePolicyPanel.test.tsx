import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import type { ApplicableTableMaintenancePolicyApiResponse, PolicyTargetApiResponse } from "../api/generated/model";
import { bodyOf, callsTo, stubCatalogApi, type StubHandler } from "../test/catalogApiStub";
import {
  DEFAULT_POLICY_ID,
  jsonResponse,
  NIGHTLY_POLICY_ID,
  policyContentFixture,
  policyFixture,
  SCRATCH_POLICY_ID,
} from "../test/fixtures";
import { ApplicablePolicyPanel, type PolicyScope } from "./ApplicablePolicyPanel";

const TABLE_SCOPE: PolicyScope = { type: "table", catalog: "iceberg", namespace: ["retail"], table: "orders", tableUuid: "uuid-orders", recorded: true };
const UNRECORDED_TABLE_SCOPE: PolicyScope = { ...TABLE_SCOPE, recorded: false };
const NAMESPACE_SCOPE: PolicyScope = { type: "namespace", catalog: "iceberg", namespace: ["retail", "eu"] };
const TABLE_APPLICABLE = "GET /v1/tables/uuid-orders/applicable-policy";
const NAMESPACE_APPLICABLE = "GET /v1/applicable-policy?catalog=iceberg&namespace=retail.eu";
const UNRECORDED_TABLE_APPLICABLE = "GET /v1/applicable-policy?catalog=iceberg&namespace=retail&table=orders";

function applicable(
  target: PolicyTargetApiResponse | null,
  overrides: Partial<ApplicableTableMaintenancePolicyApiResponse> = {},
): ApplicableTableMaintenancePolicyApiResponse {
  return { ...policyContentFixture(), id: NIGHTLY_POLICY_ID, name: "nightly", version: 4, target, ...overrides };
}

const POLICIES = [
  policyFixture({ name: "default" }),
  policyFixture({ id: NIGHTLY_POLICY_ID, name: "nightly", version: 4 }),
  policyFixture({ id: SCRATCH_POLICY_ID, name: "scratch" }),
];

function stubApi(routes: Record<string, StubHandler>) {
  return stubCatalogApi({ "GET /v1/maintenance-policies": () => jsonResponse({ policies: POLICIES }), ...routes });
}

function renderPanel(scope: PolicyScope) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ApplicablePolicyPanel scope={scope} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ApplicablePolicyPanel", () => {
  it("names the target an inherited policy comes from and offers no detach", async () => {
    stubApi({ [TABLE_APPLICABLE]: () => jsonResponse(applicable({ type: "namespace", path: ["iceberg", "retail"], table_uuid: null })) });
    renderPanel(TABLE_SCOPE);
    const origin = await screen.findByText(/Inherited from namespace/);
    expect(within(origin).getByRole("link", { name: "iceberg.retail" })).toHaveAttribute(
      "href",
      "/catalogs/iceberg/namespaces/retail",
    );
    expect(screen.getByRole("link", { name: "nightly v4" })).toHaveAttribute("href", "/policies/nightly/versions/4");
    expect(screen.getByRole("button", { name: "Attach policy" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Detach" })).not.toBeInTheDocument();
  });

  it("says the platform default applies when nothing is attached here or above", async () => {
    stubApi({ [NAMESPACE_APPLICABLE]: () => jsonResponse(applicable(null, { id: DEFAULT_POLICY_ID, name: "default", version: 3, dry_run: true })) });
    renderPanel(NAMESPACE_SCOPE);
    expect(await screen.findByText("Platform default")).toBeInTheDocument();
    expect(screen.getByText("Dry run")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Detach" })).not.toBeInTheDocument();
  });

  it("detaches a policy attached here and reads what applies again", async () => {
    const calls = stubApi({
      [TABLE_APPLICABLE]: () =>
        jsonResponse(applicable({ type: "table", path: ["iceberg", "retail", "orders"], table_uuid: "uuid-orders" })),
      "DELETE /v1/maintenance-policies/nightly/mappings": () => new Response(null, { status: 204 }),
    });
    renderPanel(TABLE_SCOPE);
    expect(await screen.findByText("Attached here")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Detach" }));
    await waitFor(() => expect(callsTo(calls, "GET", "/v1/tables/uuid-orders/applicable-policy")).toHaveLength(2));
    expect(bodyOf(calls, "DELETE", "/v1/maintenance-policies/nightly/mappings")).toEqual({
      target: { type: "table", path: ["iceberg", "retail", "orders"], table_uuid: "uuid-orders" },
    });
  });

  it("attaches the chosen policy to this target", async () => {
    const calls = stubApi({
      [NAMESPACE_APPLICABLE]: () => jsonResponse(applicable(null, { id: DEFAULT_POLICY_ID, name: "default", version: 3 })),
      "PUT /v1/maintenance-policies/scratch/mappings": () =>
        jsonResponse({ policy_name: "scratch", target: { type: "namespace", path: ["iceberg", "retail", "eu"], table_uuid: null }, attached_at: "2026-11-12T09:00:00Z" }),
    });
    renderPanel(NAMESPACE_SCOPE);
    await userEvent.click(await screen.findByRole("button", { name: "Attach policy" }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("combobox", { name: "Policy" }));
    await userEvent.click(await screen.findByRole("option", { name: "scratch" }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Attach" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(bodyOf(calls, "PUT", "/v1/maintenance-policies/scratch/mappings")).toEqual({
      target: { type: "namespace", path: ["iceberg", "retail", "eu"] },
    });
    await waitFor(() => expect(callsTo(calls, "GET", "/v1/applicable-policy?catalog=iceberg&namespace=retail.eu")).toHaveLength(2));
  });

  it("asks by name for a table maintenance has no record of, and detaches its own attachment by uuid", async () => {
    const calls = stubApi({
      [UNRECORDED_TABLE_APPLICABLE]: () =>
        jsonResponse(applicable({ type: "table", path: ["iceberg", "retail", "orders"], table_uuid: "uuid-orders" })),
      "DELETE /v1/maintenance-policies/nightly/mappings": () => new Response(null, { status: 204 }),
    });
    renderPanel(UNRECORDED_TABLE_SCOPE);
    expect(await screen.findByText("Attached here")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Detach" }));
    await waitFor(() =>
      expect(callsTo(calls, "GET", "/v1/applicable-policy?catalog=iceberg&namespace=retail&table=orders")).toHaveLength(2),
    );
    expect(bodyOf(calls, "DELETE", "/v1/maintenance-policies/nightly/mappings")).toEqual({
      target: { type: "table", path: ["iceberg", "retail", "orders"], table_uuid: "uuid-orders" },
    });
    expect(callsTo(calls, "GET", "/v1/tables/uuid-orders/applicable-policy")).toHaveLength(0);
  });
});
