import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import {
  useListScannedCatalogs,
  useListTableDiscoveryPolicyAttachments,
} from "../api/generated/discovery-policies/discovery-policies";
import { bodyOf, callsTo, catalogFixture, stubCatalogApi, type StubHandler } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { AttachDiscoveryPolicyDialog } from "./AttachDiscoveryPolicyDialog";

const ATTACHMENTS = "/v1/discovery-policies/sales-tables/attachments";

function attached(body: unknown): Response {
  const { target } = body as { target: { type: string; path: string[] } };
  return jsonResponse({
    id: "da-01m7s6c3tqee0rhg00xry2zqqx",
    policy_id: "dp-01m7s6c3tqee0rhg00xry2zqqv",
    policy_name: "sales-tables",
    target: { ...target, table_uuid: null },
    attached_at: "2026-11-21T09:00:00Z",
  });
}

// What the policy page reads beside the dialog, so a test sees which of them an attach refetches.
function PageReads() {
  useListTableDiscoveryPolicyAttachments("sales-tables");
  useListScannedCatalogs();
  return null;
}

function renderDialog(attach: StubHandler = attached, responses: Record<string, StubHandler> = {}) {
  const calls = stubCatalogApi({
    "GET /v1/catalogs": () => jsonResponse([catalogFixture(), catalogFixture({ name: "analytics" })]),
    [`GET ${ATTACHMENTS}`]: () => jsonResponse({ attachments: [] }),
    "GET /v1/scanned-catalogs": () => jsonResponse({ catalogs: [] }),
    [`PUT ${ATTACHMENTS}`]: attach,
    ...responses,
  });
  const onClose = vi.fn();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <PageReads />
      <AttachDiscoveryPolicyDialog policyName="sales-tables" onClose={onClose} />
    </QueryClientProvider>,
  );
  return { calls, onClose, client };
}

function dialog(): HTMLElement {
  return screen.getByRole("dialog", { name: "Attach sales-tables" });
}

async function choose(user: ReturnType<typeof userEvent.setup>, field: string, option: string) {
  await user.click(await within(dialog()).findByRole("combobox", { name: field }));
  await user.click(await screen.findByRole("option", { name: option }));
}

describe("AttachDiscoveryPolicyDialog", { timeout: 15_000 }, () => {
  it("says an attach replaces the policy the target has", () => {
    renderDialog();
    expect(within(dialog()).getByText(/replaces the policy the target has\./)).toBeInTheDocument();
  });

  it("starts on a catalog, asking only which one", async () => {
    renderDialog();
    expect(within(dialog()).getByRole("combobox", { name: "Type" })).toHaveTextContent("Catalog");
    expect(await within(dialog()).findByRole("combobox", { name: "Catalog" })).toBeInTheDocument();
    expect(within(dialog()).queryByRole("textbox", { name: "Namespace" })).not.toBeInTheDocument();
    expect(within(dialog()).queryByRole("textbox", { name: "Table" })).not.toBeInTheDocument();
  });

  it("offers only the catalogs Polaris has", async () => {
    const user = userEvent.setup();
    renderDialog();
    await user.click(await within(dialog()).findByRole("combobox", { name: "Catalog" }));
    const options = await screen.findAllByRole("option");
    expect(options.map((option) => option.textContent)).toEqual(["analytics", "iceberg"]);
  });

  it("asks for the namespace of a namespace, and for its table too for a table", async () => {
    const user = userEvent.setup();
    renderDialog();
    await choose(user, "Type", "Namespace");
    expect(within(dialog()).getByRole("textbox", { name: "Namespace" })).toBeInTheDocument();
    expect(within(dialog()).queryByRole("textbox", { name: "Table" })).not.toBeInTheDocument();
    await choose(user, "Type", "Table");
    expect(within(dialog()).getByRole("textbox", { name: "Namespace" })).toBeInTheDocument();
    expect(within(dialog()).getByRole("textbox", { name: "Table" })).toBeInTheDocument();
  });

  it("attaches to a catalog and closes", async () => {
    const user = userEvent.setup();
    const { calls, onClose } = renderDialog();
    await choose(user, "Catalog", "iceberg");
    await user.click(within(dialog()).getByRole("button", { name: "Attach" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(bodyOf(calls, "PUT", ATTACHMENTS)).toEqual({ target: { type: "catalog", path: ["iceberg"] } });
  });

  it("splits a dot-joined namespace into its levels", async () => {
    const user = userEvent.setup();
    const { calls, onClose } = renderDialog();
    await choose(user, "Type", "Namespace");
    await choose(user, "Catalog", "iceberg");
    await user.type(within(dialog()).getByRole("textbox", { name: "Namespace" }), " sales.eu ");
    await user.click(within(dialog()).getByRole("button", { name: "Attach" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(bodyOf(calls, "PUT", ATTACHMENTS)).toEqual({ target: { type: "namespace", path: ["iceberg", "sales", "eu"] } });
  });

  it("attaches to a table by its catalog, namespace and name", async () => {
    const user = userEvent.setup();
    const { calls, onClose } = renderDialog();
    await choose(user, "Type", "Table");
    await choose(user, "Catalog", "iceberg");
    await user.type(within(dialog()).getByRole("textbox", { name: "Namespace" }), "finance");
    await user.type(within(dialog()).getByRole("textbox", { name: "Table" }), "ledger");
    await user.click(within(dialog()).getByRole("button", { name: "Attach" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(bodyOf(calls, "PUT", ATTACHMENTS)).toEqual({
      target: { type: "table", path: ["iceberg", "finance", "ledger"] },
    });
  });

  it.each([
    ["Catalog", [], "Choose a catalog."],
    ["Namespace", ["catalog"], "Enter the namespace, its levels joined by dots."],
    ["Namespace", ["catalog", "namespace:sales..eu"], "Enter the namespace, its levels joined by dots."],
    ["Table", ["catalog", "namespace:finance"], "Enter the table's name."],
  ])("refuses a %s target left incomplete without asking the API", async (type, filled, message) => {
    const user = userEvent.setup();
    const { calls, onClose } = renderDialog();
    if (type !== "Catalog") await choose(user, "Type", type);
    for (const field of filled) {
      if (field === "catalog") await choose(user, "Catalog", "iceberg");
      else await user.type(within(dialog()).getByRole("textbox", { name: "Namespace" }), field.slice("namespace:".length));
    }
    await user.click(within(dialog()).getByRole("button", { name: "Attach" }));

    expect(await within(dialog()).findByText(message)).toBeInTheDocument();
    expect(callsTo(calls, "PUT", ATTACHMENTS)).toEqual([]);
    expect(onClose).not.toHaveBeenCalled();
  });

  it.each([
    [404, "namespace iceberg.sales.eu not found"],
    [403, "the platform's catalog credential cannot read catalog iceberg"],
  ])("shows the API's detail for a %i inside the dialog and stays open", async (status, detail) => {
    const user = userEvent.setup();
    const { onClose } = renderDialog(() => jsonResponse({ detail }, status));
    await choose(user, "Catalog", "iceberg");
    await user.click(within(dialog()).getByRole("button", { name: "Attach" }));

    expect(await within(dialog()).findByText(detail)).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it.each([
    ["succeeds", attached],
    ["fails", () => jsonResponse({ detail: "catalog iceberg not found" }, 404)],
  ])("refetches the attachments, the policies and the scan states when an attach %s", async (_outcome, attach) => {
    const user = userEvent.setup();
    const { calls, client } = renderDialog(attach);
    const invalidate = vi.spyOn(client, "invalidateQueries");
    await waitFor(() => expect(callsTo(calls, "GET", ATTACHMENTS)).toHaveLength(1));
    await choose(user, "Catalog", "iceberg");
    await user.click(within(dialog()).getByRole("button", { name: "Attach" }));

    await waitFor(() => expect(callsTo(calls, "GET", ATTACHMENTS)).toHaveLength(2));
    await waitFor(() => expect(callsTo(calls, "GET", "/v1/scanned-catalogs")).toHaveLength(2));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["/v1/discovery-policies"], exact: true });
  });

  it("says so when the catalogs cannot be read", async () => {
    renderDialog(attached, { "GET /v1/catalogs": () => jsonResponse({ detail: "Polaris unavailable" }, 502) });
    expect(await within(dialog()).findByText("Could not load catalogs: Polaris unavailable")).toBeInTheDocument();
  });

  it("is filled and sent from the keyboard alone", async () => {
    const user = userEvent.setup();
    const { calls, onClose } = renderDialog();
    await within(dialog()).findByRole("combobox", { name: "Catalog" });
    await waitFor(() => expect(within(dialog()).getByRole("button", { name: "Close" })).toHaveFocus());
    await user.tab();
    expect(within(dialog()).getByRole("combobox", { name: "Type" })).toHaveFocus();
    await user.keyboard("{Enter}");
    await screen.findByRole("listbox");
    await user.keyboard("{ArrowDown}{ArrowDown}{Enter}");
    await waitFor(() => expect(within(dialog()).getByRole("combobox", { name: "Type" })).toHaveTextContent("Table"));
    await user.tab();
    expect(within(dialog()).getByRole("combobox", { name: "Catalog" })).toHaveFocus();
    await user.keyboard("{Enter}");
    await screen.findByRole("listbox");
    await user.keyboard("{ArrowDown}{Enter}");
    await waitFor(() => expect(within(dialog()).getByRole("combobox", { name: "Catalog" })).toHaveTextContent("iceberg"));
    await user.tab();
    expect(within(dialog()).getByRole("textbox", { name: "Namespace" })).toHaveFocus();
    await user.keyboard("finance");
    await user.tab();
    expect(within(dialog()).getByRole("textbox", { name: "Table" })).toHaveFocus();
    await user.keyboard("ledger");
    await user.tab();
    expect(within(dialog()).getByRole("button", { name: "Cancel" })).toHaveFocus();
    await user.tab();
    expect(within(dialog()).getByRole("button", { name: "Attach" })).toHaveFocus();
    await user.keyboard("{Enter}");

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(bodyOf(calls, "PUT", ATTACHMENTS)).toEqual({
      target: { type: "table", path: ["iceberg", "finance", "ledger"] },
    });
  });
});
