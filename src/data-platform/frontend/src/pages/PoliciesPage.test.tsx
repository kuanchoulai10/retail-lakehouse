import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import type { ListedTableMaintenancePolicyMappingApiResponse } from "../api/generated/model";
import { bodyOf, callsTo, stubCatalogApi, type StubHandler } from "../test/catalogApiStub";
import {
  jsonResponse,
  NIGHTLY_POLICY_ID,
  policyContentFixture,
  policyFixture,
  SCRATCH_POLICY_ID,
} from "../test/fixtures";
import { PoliciesPage } from "./PoliciesPage";

const POLICIES = [
  policyFixture({
    id: NIGHTLY_POLICY_ID,
    name: "nightly",
    description: "Nightly compaction",
    version: 4,
    attachment_count: 2,
    priority: "P0",
  }),
  policyFixture({ name: "default", description: "Platform default", version: 3, attachment_count: 0 }),
  policyFixture({ id: SCRATCH_POLICY_ID, name: "scratch", description: "", version: 1, attachment_count: 0 }),
];

function mapping(
  target: ListedTableMaintenancePolicyMappingApiResponse["target"],
  orphaned = false,
): ListedTableMaintenancePolicyMappingApiResponse {
  return { policy_id: NIGHTLY_POLICY_ID, policy_name: "nightly", target, orphaned, attached_at: "2026-11-03T09:00:00Z" };
}

const NIGHTLY_MAPPINGS = [
  mapping({ type: "namespace", path: ["iceberg", "retail"], table_uuid: null }),
  mapping({ type: "catalog", path: ["legacy"], table_uuid: null }, true),
];

function stubApi(responses: Record<string, StubHandler> = {}) {
  return stubCatalogApi({
    "GET /v1/maintenance-policies": () => jsonResponse({ policies: POLICIES }),
    "GET /v1/maintenance-policies/nightly/mappings": () => jsonResponse({ mappings: NIGHTLY_MAPPINGS }),
    ...responses,
  });
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <PoliciesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function policyRow(name: string): HTMLElement {
  const row = screen
    .getAllByRole("row")
    .find((r) => within(r).queryAllByRole("cell")[0]?.textContent?.startsWith(name));
  if (row === undefined) throw new Error(`no policy ${name}`);
  return row;
}

describe("PoliciesPage", () => {
  it("lists the policies with the default first and tagged", async () => {
    stubApi();
    renderPage();
    await screen.findByText("Nightly compaction");
    const names = screen
      .getAllByRole("row")
      .slice(1)
      .map((row) => within(row).getAllByRole("cell")[0]?.textContent);
    expect(names).toEqual(["defaultDefault", "nightly", "scratch"]);
    expect(within(policyRow("default")).getByText("Default")).toBeInTheDocument();
    expect(within(policyRow("nightly")).queryByText("Default")).not.toBeInTheDocument();
    expect(within(policyRow("nightly")).getByText("4")).toBeInTheDocument();
  });

  it("shows each policy's priority as it is", async () => {
    stubApi();
    renderPage();
    await screen.findByText("Nightly compaction");
    expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toContain("Priority");
    expect(await within(policyRow("nightly")).findByText("P0")).toBeInTheDocument();
    expect(within(policyRow("default")).getByText("P2")).toBeInTheDocument();
  });

  it("shows where each policy is attached, marking a target no longer in the catalog", async () => {
    const calls = stubApi();
    renderPage();
    const row = await screen.findByText("Nightly compaction").then(() => policyRow("nightly"));
    const retail = await within(row).findByRole("link", { name: "iceberg.retail" });
    expect(retail).toHaveAttribute("href", "/catalogs/iceberg/namespaces/retail");
    expect(within(row).getByText("Namespace")).toBeInTheDocument();
    expect(within(row).getByText("legacy")).toBeInTheDocument();
    expect(within(row).queryByRole("link", { name: "legacy" })).not.toBeInTheDocument();
    expect(within(row).getByText("No longer in the catalog")).toBeInTheDocument();
    expect(within(policyRow("scratch")).getByText("Not attached")).toBeInTheDocument();
    expect(calls.filter((call) => call.path.endsWith("/mappings")).map((call) => call.path)).toEqual([
      "/v1/maintenance-policies/nightly/mappings",
    ]);
  });

  it("creates a policy from the default's content and refetches the list", async () => {
    const calls = stubApi({
      "POST /v1/maintenance-policies": () => jsonResponse(policyFixture({ name: "weekly", version: 1 }), 201),
    });
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: "New policy" }));
    const dialog = await screen.findByRole("dialog", { name: "New policy" });
    await user.type(within(dialog).getByRole("textbox", { name: "Name" }), "weekly");
    await user.click(within(dialog).getByRole("button", { name: "Create policy" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(bodyOf(calls, "POST", "/v1/maintenance-policies")).toEqual({
      ...policyContentFixture(),
      description: "",
      name: "weekly",
    });
    await waitFor(() => expect(callsTo(calls, "GET", "/v1/maintenance-policies")).toHaveLength(2));
  });

  it("edits a policy sending the version it read", async () => {
    const calls = stubApi({
      "PUT /v1/maintenance-policies/nightly": () => jsonResponse({ ...POLICIES[0], version: 5 }),
    });
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Nightly compaction");
    await user.click(within(policyRow("nightly")).getByRole("button", { name: "Edit nightly" }));
    const dialog = await screen.findByRole("dialog", { name: "Edit policy" });
    await user.click(within(dialog).getByRole("button", { name: "Save" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(bodyOf(calls, "PUT", "/v1/maintenance-policies/nightly")).toMatchObject({ version: 4 });
    await waitFor(() => expect(callsTo(calls, "GET", "/v1/maintenance-policies")).toHaveLength(2));
  });

  it("disables delete of the default policy with its reason", async () => {
    stubApi();
    renderPage();
    await screen.findByText("Nightly compaction");
    const remove = within(policyRow("default")).getByRole("button", { name: "Delete default" });
    expect(remove).toBeDisabled();
    expect(remove).toHaveAccessibleDescription("The default policy cannot be deleted.");
  });

  it("tells the default by the flag the API sets, not by its name", async () => {
    stubApi({
      "GET /v1/maintenance-policies": () =>
        jsonResponse({
          policies: [
            policyFixture({ name: "platform", description: "Platform default", is_default: true }),
            policyFixture({ id: SCRATCH_POLICY_ID, name: "default", description: "Named default", is_default: false }),
          ],
        }),
    });
    renderPage();
    await screen.findByText("Named default");
    const names = screen
      .getAllByRole("row")
      .slice(1)
      .map((row) => within(row).getAllByRole("cell")[0]?.textContent);
    expect(names).toEqual(["platformDefault", "default"]);
    expect(within(policyRow("platform")).getByRole("button", { name: "Delete platform" })).toBeDisabled();
    expect(within(policyRow("default")).getByRole("button", { name: "Delete default" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "New policy" })).toBeEnabled();
  });

  it("disables delete of an attached policy with its reason", async () => {
    stubApi();
    renderPage();
    await screen.findByText("Nightly compaction");
    const remove = within(policyRow("nightly")).getByRole("button", { name: "Delete nightly" });
    expect(remove).toBeDisabled();
    expect(remove).toHaveAccessibleDescription("Detach it from every target before deleting it.");
  });

  it("deletes an unattached policy once its name is typed", async () => {
    const calls = stubApi({
      "DELETE /v1/maintenance-policies/scratch": () => new Response(null, { status: 204 }),
    });
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Nightly compaction");
    await user.click(within(policyRow("scratch")).getByRole("button", { name: "Delete scratch" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Delete policy" });
    expect(within(dialog).getByText(/and every version of it/)).toBeInTheDocument();
    await user.type(within(dialog).getByRole("textbox", { name: "Type scratch to confirm" }), "scratch");
    await user.click(within(dialog).getByRole("button", { name: "Delete" }));

    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
    expect(callsTo(calls, "DELETE", "/v1/maintenance-policies/scratch")).toHaveLength(1);
    await waitFor(() => expect(callsTo(calls, "GET", "/v1/maintenance-policies")).toHaveLength(2));
  });

  it("disables New policy and says why when the list has no default to start from", async () => {
    stubApi({
      "GET /v1/maintenance-policies": () =>
        jsonResponse({ policies: POLICIES.filter((policy) => policy.name !== "default") }),
    });
    renderPage();
    await screen.findByText("Nightly compaction");
    expect(screen.getByRole("button", { name: "New policy" })).toBeDisabled();
    expect(
      screen.getByText("The default policy is missing, so a new policy has nothing to start from. Reload the page."),
    ).toBeInTheDocument();
  });

  it("shows an error when the policies cannot be loaded", async () => {
    stubApi({ "GET /v1/maintenance-policies": () => jsonResponse({ detail: "boom" }, 500) });
    renderPage();
    expect(await screen.findByText("Could not load policies: boom")).toBeInTheDocument();
  });
});
