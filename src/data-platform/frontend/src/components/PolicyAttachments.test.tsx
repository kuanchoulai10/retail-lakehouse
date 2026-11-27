import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import {
  getListTableMaintenancePoliciesQueryKey,
  getListTableMaintenancePolicyAttachmentsQueryKey,
} from "../api/generated/maintenance-policies/maintenance-policies";
import type { ListedTableMaintenancePolicyAttachmentApiResponse, PolicyTargetApiResponse } from "../api/generated/model";
import { getGetTableQueryKey } from "../api/generated/tables/tables";
import { callsTo, stubCatalogApi, type StubHandler } from "../test/catalogApiStub";
import { jsonResponse, NIGHTLY_POLICY_ID } from "../test/fixtures";
import { PolicyAttachments } from "./PolicyAttachments";

const ATTACHMENTS = "/v1/maintenance-policies/nightly/attachments";
// A detach names the place by its type and path, the path repeated once per part.
const DETACH_RETAIL = `${ATTACHMENTS}?target_type=namespace&path=iceberg&path=retail`;
const DETACH_LEGACY = `${ATTACHMENTS}?target_type=catalog&path=legacy`;

function attachment(target: PolicyTargetApiResponse, orphaned = false): ListedTableMaintenancePolicyAttachmentApiResponse {
  return { policy_id: NIGHTLY_POLICY_ID, policy_name: "nightly", target, orphaned };
}

const RETAIL = attachment({ type: "namespace", path: ["iceberg", "retail"], table_uuid: null });
// Its catalog left Polaris: no page links it, so only this list can detach the policy from it.
const LEGACY = attachment({ type: "catalog", path: ["legacy"], table_uuid: null }, true);

function stubApi(attachments: () => ListedTableMaintenancePolicyAttachmentApiResponse[], routes: Record<string, StubHandler> = {}) {
  return stubCatalogApi({
    [`GET ${ATTACHMENTS}`]: () => jsonResponse({ attachments: attachments() }),
    ...routes,
  });
}

function renderAttachments(count: number) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <PolicyAttachments name="nightly" count={count} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return client;
}

describe("PolicyAttachments", { timeout: 15_000 }, () => {
  it("offers Detach on every place, its name starting with the visible label", async () => {
    stubApi(() => [RETAIL, LEGACY]);
    renderAttachments(2);
    const retail = await screen.findByRole("button", { name: "Detach nightly from iceberg.retail" });
    expect(retail).toHaveTextContent(/^Detach$/);
    expect(screen.getByRole("button", { name: "Detach nightly from legacy" })).toBeInTheDocument();
  });

  it("detaches by the row's place without asking, then refetches the policy's places, the policy list and the table records", async () => {
    let attachments = [RETAIL, LEGACY];
    const calls = stubApi(() => attachments, {
      [`DELETE ${DETACH_RETAIL}`]: () => {
        attachments = [LEGACY];
        return new Response(null, { status: 204 });
      },
    });
    const user = userEvent.setup();
    const client = renderAttachments(2);
    client.setQueryData(getListTableMaintenancePoliciesQueryKey(), {});
    client.setQueryData(getGetTableQueryKey("uuid-orders"), {});
    const invalidate = vi.spyOn(client, "invalidateQueries");
    await user.click(await screen.findByRole("button", { name: "Detach nightly from iceberg.retail" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("button", { name: "Detach nightly from iceberg.retail" })).not.toBeInTheDocument());
    expect(callsTo(calls, "DELETE", DETACH_RETAIL)).toHaveLength(1);
    expect(callsTo(calls, "GET", ATTACHMENTS)).toHaveLength(2);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: getListTableMaintenancePoliciesQueryKey(), exact: true });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: getListTableMaintenancePolicyAttachmentsQueryKey("nightly") });
    expect(client.getQueryState(getGetTableQueryKey("uuid-orders"))?.isInvalidated).toBe(true);
  });

  it("detaches an orphaned place, which no page links, by its type and path", async () => {
    const calls = stubApi(() => [RETAIL, LEGACY], {
      [`DELETE ${DETACH_LEGACY}`]: () => new Response(null, { status: 204 }),
    });
    const user = userEvent.setup();
    renderAttachments(2);
    expect(await screen.findByText("No longer in the catalog")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Detach nightly from legacy" }));

    await waitFor(() => expect(callsTo(calls, "DELETE", DETACH_LEGACY)).toHaveLength(1));
    expect(calls.filter((call) => call.method === "DELETE")).toHaveLength(1);
  });

  it("moves focus to the next place's Detach once a place is detached", async () => {
    let attachments = [RETAIL, LEGACY];
    stubApi(() => attachments, {
      [`DELETE ${DETACH_RETAIL}`]: () => {
        attachments = [LEGACY];
        return new Response(null, { status: 204 });
      },
    });
    const user = userEvent.setup();
    renderAttachments(2);
    (await screen.findByRole("button", { name: "Detach nightly from iceberg.retail" })).focus();
    await user.keyboard("{Enter}");

    await waitFor(() => expect(screen.getByRole("button", { name: "Detach nightly from legacy" })).toHaveFocus());
  });

  it("keeps focus in the list once its last place is detached", async () => {
    let attachments = [LEGACY];
    stubApi(() => attachments, {
      [`DELETE ${DETACH_LEGACY}`]: () => {
        attachments = [];
        return new Response(null, { status: 204 });
      },
    });
    const user = userEvent.setup();
    renderAttachments(1);
    (await screen.findByRole("button", { name: "Detach nightly from legacy" })).focus();
    await user.keyboard("{Enter}");

    const list = await screen.findByRole("group", { name: "Where nightly is attached" });
    await waitFor(() => expect(list).toHaveFocus());
    expect(screen.queryByRole("button", { name: /^Detach/ })).not.toBeInTheDocument();
  });

  it("shows a refused detach, refetches anyway and gives focus back to that Detach", async () => {
    const calls = stubApi(() => [RETAIL, LEGACY], {
      // A browser drops focus from the button it disables while the detach runs; jsdom keeps it.
      [`DELETE ${DETACH_LEGACY}`]: () => {
        (document.activeElement as HTMLElement | null)?.blur();
        return jsonResponse({ detail: "database unavailable" }, 500);
      },
    });
    const user = userEvent.setup();
    renderAttachments(2);
    const detach = await screen.findByRole("button", { name: "Detach nightly from legacy" });
    detach.focus();
    await user.keyboard("{Enter}");

    expect(await screen.findByText("Could not detach nightly from legacy: database unavailable")).toBeInTheDocument();
    await waitFor(() => expect(callsTo(calls, "GET", ATTACHMENTS)).toHaveLength(2));
    await waitFor(() => expect(screen.getByRole("button", { name: "Detach nightly from legacy" })).toHaveFocus());
  });

  it("says not attached, with nothing to detach, and does not read the places", async () => {
    const calls = stubApi(() => []);
    renderAttachments(0);
    expect(screen.getByText("Not attached")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(callsTo(calls, "GET", ATTACHMENTS)).toHaveLength(0);
  });

  it("keeps two table rows of one path apart, an old record and a recreated table", async () => {
    const path = ["iceberg", "retail", "orders"];
    const errors = vi.spyOn(console, "error").mockImplementation(() => {});
    stubApi(() => [
      attachment({ type: "table", path, table_uuid: "uuid-orders-old" }, true),
      attachment({ type: "table", path, table_uuid: "uuid-orders" }),
    ]);
    renderAttachments(2);

    expect(await screen.findAllByRole("button", { name: "Detach nightly from iceberg.retail.orders" })).toHaveLength(2);
    expect(errors.mock.calls.flat().join(" ")).not.toMatch(/same key/);
    errors.mockRestore();
  });
});
