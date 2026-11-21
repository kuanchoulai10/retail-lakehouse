import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import type {
  ListedTableDiscoveryPolicyAttachmentApiResponse,
  ScannedCatalogApiResponse,
} from "../api/generated/model";
import { callsTo, catalogFixture, stubCatalogApi, type StubHandler } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { DiscoveryPolicyAttachments } from "./DiscoveryPolicyAttachments";

const ATTACHMENTS = "/v1/discovery-policies/sales-tables/attachments";

function attachment(
  overrides: Partial<ListedTableDiscoveryPolicyAttachmentApiResponse> = {},
): ListedTableDiscoveryPolicyAttachmentApiResponse {
  return {
    id: "da-01m7s6c3tqee0rhg00xry2zqqx",
    policy_id: "dp-01m7s6c3tqee0rhg00xry2zqqv",
    policy_name: "sales-tables",
    target: { type: "namespace", path: ["iceberg", "sales"], table_uuid: null },
    orphaned: false,
    attached_at: "2026-11-05T09:00:00Z",
    ...overrides,
  };
}

const CATALOG = attachment({ id: "da-catalog", target: { type: "catalog", path: ["analytics"], table_uuid: null } });
const NAMESPACE = attachment({ id: "da-namespace" });
const TABLE = attachment({
  id: "da-table",
  target: { type: "table", path: ["iceberg", "finance", "ledger"], table_uuid: "uuid-ledger" },
});

function scanned(catalog: string, overrides: Partial<ScannedCatalogApiResponse> = {}): ScannedCatalogApiResponse {
  return { catalog, last_discovered_at: new Date(Date.now() - 5 * 60_000).toISOString(), failure: null, ...overrides };
}

function stubApi(
  attachments: ListedTableDiscoveryPolicyAttachmentApiResponse[],
  catalogs: ScannedCatalogApiResponse[] = [scanned("iceberg"), scanned("analytics")],
  responses: Record<string, StubHandler> = {},
) {
  return stubCatalogApi({
    [`GET ${ATTACHMENTS}`]: () => jsonResponse({ attachments }),
    "GET /v1/scanned-catalogs": () => jsonResponse({ catalogs }),
    "GET /v1/catalogs": () => jsonResponse([catalogFixture(), catalogFixture({ name: "analytics" })]),
    "GET /v1/discovery-policies": () => jsonResponse({ policies: [] }),
    ...responses,
  });
}

function renderAttachments() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <DiscoveryPolicyAttachments policyName="sales-tables" />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { client };
}

function section(): HTMLElement {
  return screen.getByRole("region", { name: "Attached to" });
}

async function row(name: string): Promise<HTMLElement> {
  const detach = await screen.findByRole("button", { name: `Detach from ${name}` });
  const item = detach.closest("li");
  if (item === null) throw new Error(`no row for ${name}`);
  return item;
}

describe("DiscoveryPolicyAttachments", { timeout: 15_000 }, () => {
  it("says the policy is attached nowhere, and how to apply it", async () => {
    stubApi([]);
    renderAttachments();
    expect(
      await screen.findByText("Not attached. Attach it to a catalog, namespace or table to apply it."),
    ).toBeInTheDocument();
    expect(within(section()).getByRole("button", { name: "Attach" })).toBeEnabled();
  });

  it("lists each target with its kind and a link to its page", async () => {
    stubApi([CATALOG, NAMESPACE, TABLE]);
    renderAttachments();
    const catalog = await row("analytics");
    expect(within(catalog).getByText("Catalog")).toBeInTheDocument();
    expect(within(catalog).getByRole("link", { name: "analytics" })).toHaveAttribute("href", "/catalogs/analytics");
    const namespace = await row("iceberg.sales");
    expect(within(namespace).getByText("Namespace")).toBeInTheDocument();
    expect(within(namespace).getByRole("link", { name: "iceberg.sales" })).toHaveAttribute(
      "href",
      "/catalogs/iceberg/namespaces/sales",
    );
    const table = await row("iceberg.finance.ledger");
    expect(within(table).getByText("Table")).toBeInTheDocument();
    expect(within(table).getByRole("link", { name: "iceberg.finance.ledger" })).toHaveAttribute(
      "href",
      "/catalogs/iceberg/namespaces/finance/tables/ledger",
    );
    expect(screen.queryByText("Orphaned")).not.toBeInTheDocument();
  });

  it("marks a target that left the catalog as orphaned, without a link", async () => {
    stubApi([attachment({ orphaned: true })]);
    renderAttachments();
    const orphaned = await row("iceberg.sales");
    expect(within(orphaned).getByText("Orphaned")).toBeInTheDocument();
    expect(within(orphaned).queryByRole("link")).not.toBeInTheDocument();
    expect(within(orphaned).getByText("iceberg.sales")).toHaveClass("font-mono");
  });

  it("says when its catalog was last scanned", async () => {
    stubApi([NAMESPACE]);
    renderAttachments();
    const namespace = await row("iceberg.sales");
    const state = await within(namespace).findByText(/^Scanned/);
    expect(state).toHaveTextContent("Scanned 5 min ago");
    expect(within(state).getByText("5 min ago").tagName).toBe("TIME");
  });

  it("says when its catalog is to be scanned but has not been yet", async () => {
    stubApi([NAMESPACE], [scanned("iceberg", { last_discovered_at: null })]);
    renderAttachments();
    const namespace = await row("iceberg.sales");
    expect(await within(namespace).findByText("Not scanned yet")).toBeInTheDocument();
  });

  it("says when no policy in its catalog manages tables, so discovery does not scan it", async () => {
    stubApi([CATALOG], [scanned("iceberg")]);
    renderAttachments();
    const catalog = await row("analytics");
    const state = await within(catalog).findByText(/^Not scanned: no policy in/);
    expect(state).toHaveTextContent("Not scanned: no policy in analytics manages tables");
    expect(within(state).getByText("analytics")).toHaveClass("font-mono");
  });

  it("says, as an error, when discovery cannot access its catalog", async () => {
    stubApi(
      [NAMESPACE],
      [
        scanned("iceberg", {
          failure: {
            reason: "cannot_access",
            detail: "the platform's catalog credential cannot read catalog iceberg",
            failed_at: "2026-11-21T09:00:00Z",
          },
        }),
      ],
    );
    renderAttachments();
    const namespace = await row("iceberg.sales");
    const label = await within(namespace).findByText("Cannot access");
    expect(label).toHaveClass("text-negative-text");
    expect(within(namespace).getByText(/the platform's catalog credential cannot read catalog iceberg/)).toBeInTheDocument();
    expect(within(namespace).queryByText(/^Scanned/)).not.toBeInTheDocument();
  });

  it("says, as an error, when its catalog is gone", async () => {
    stubApi(
      [CATALOG],
      [
        scanned("analytics", {
          failure: { reason: "not_found", detail: "catalog analytics not found", failed_at: "2026-11-21T09:00:00Z" },
        }),
      ],
    );
    renderAttachments();
    const catalog = await row("analytics");
    expect(await within(catalog).findByText("Catalog not found")).toHaveClass("text-negative-text");
    expect(within(catalog).getByText(/catalog analytics not found/)).toBeInTheDocument();
  });

  it("says a catalog cannot be accessed even when no scan of it has completed yet", async () => {
    stubApi(
      [NAMESPACE],
      [
        scanned("iceberg", {
          last_discovered_at: null,
          failure: {
            reason: "cannot_access",
            detail: "the platform's catalog credential cannot read catalog iceberg",
            failed_at: "2026-11-21T09:00:00Z",
          },
        }),
      ],
    );
    renderAttachments();
    const namespace = await row("iceberg.sales");
    expect(await within(namespace).findByText("Cannot access")).toBeInTheDocument();
    expect(within(namespace).queryByText("Not scanned yet")).not.toBeInTheDocument();
  });

  it("says so when the scan states cannot be read, and still lists the targets", async () => {
    stubApi([NAMESPACE], [], {
      "GET /v1/scanned-catalogs": () => jsonResponse({ detail: "database unavailable" }, 500),
    });
    renderAttachments();
    expect(await screen.findByText("Could not load each catalog's scan state: database unavailable")).toBeInTheDocument();
    expect(await row("iceberg.sales")).toBeInTheDocument();
  });

  it("says so when the attachments cannot be read", async () => {
    stubApi([], [], { [`GET ${ATTACHMENTS}`]: () => jsonResponse({ detail: "database unavailable" }, 500) });
    renderAttachments();
    expect(await screen.findByText("Could not load where sales-tables is attached: database unavailable")).toBeInTheDocument();
  });

  it("detaches by the attachment's id without asking, then refetches the attachments, the policies and the scan states", async () => {
    let attachments = [NAMESPACE, CATALOG];
    const calls = stubCatalogApi({
      [`GET ${ATTACHMENTS}`]: () => jsonResponse({ attachments }),
      "GET /v1/scanned-catalogs": () => jsonResponse({ catalogs: [scanned("iceberg")] }),
      [`DELETE ${ATTACHMENTS}/da-namespace`]: () => {
        attachments = [CATALOG];
        return new Response(null, { status: 204 });
      },
    });
    const user = userEvent.setup();
    const { client } = renderAttachments();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    await user.click(await screen.findByRole("button", { name: "Detach from iceberg.sales" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("button", { name: "Detach from iceberg.sales" })).not.toBeInTheDocument());
    expect(callsTo(calls, "DELETE", `${ATTACHMENTS}/da-namespace`)).toHaveLength(1);
    expect(callsTo(calls, "GET", ATTACHMENTS)).toHaveLength(2);
    expect(callsTo(calls, "GET", "/v1/scanned-catalogs")).toHaveLength(2);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["/v1/discovery-policies"], exact: true });
    expect(within(section()).getByRole("button", { name: "Attach" })).toHaveFocus();
  });

  it("shows a refused detach and refetches anyway", async () => {
    const calls = stubApi([NAMESPACE], [scanned("iceberg")], {
      [`DELETE ${ATTACHMENTS}/da-namespace`]: () =>
        jsonResponse({ detail: "discovery attachment da-namespace not found" }, 404),
    });
    const user = userEvent.setup();
    renderAttachments();
    await user.click(await screen.findByRole("button", { name: "Detach from iceberg.sales" }));

    expect(
      await screen.findByText("Could not detach from iceberg.sales: discovery attachment da-namespace not found"),
    ).toBeInTheDocument();
    await waitFor(() => expect(callsTo(calls, "GET", ATTACHMENTS)).toHaveLength(2));
    expect(callsTo(calls, "GET", "/v1/scanned-catalogs")).toHaveLength(2);
  });

  it("opens the attach dialog", async () => {
    stubApi([]);
    const user = userEvent.setup();
    renderAttachments();
    await user.click(await within(section()).findByRole("button", { name: "Attach" }));
    expect(await screen.findByRole("dialog", { name: "Attach sales-tables" })).toBeInTheDocument();
  });
});
