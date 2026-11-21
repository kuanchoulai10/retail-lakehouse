import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";
import type {
  ListedTableDiscoveryPolicyAttachmentApiResponse,
  TableDiscoveryPolicyApiResponse,
} from "../api/generated/model";
import { callsTo, stubCatalogApi, type StubHandler } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { DiscoveryPolicyPage } from "./DiscoveryPolicyPage";

const PATH = "/v1/discovery-policies/sales-tables";

function policy(overrides: Partial<TableDiscoveryPolicyApiResponse> = {}): TableDiscoveryPolicyApiResponse {
  return {
    id: "dp-01m7s6c3tqee0rhg00xry2zqqv",
    name: "sales-tables",
    is_default: false,
    version: 3,
    description: "Sales tables",
    no_match_outcome: "unmanage",
    rules: [
      {
        id: "dr-orders",
        outcome: "manage",
        conditions: [
          { attribute: "namespace", operator: "glob", values: ["sales"] },
          { attribute: "table_name", operator: "glob", values: ["orders*"] },
        ],
      },
      {
        id: "dr-temporary",
        outcome: "unmanage",
        conditions: [{ attribute: "table_name", operator: "glob", values: ["tmp_*"] }],
      },
    ],
    created_at: "2026-11-01T09:00:00Z",
    updated_at: "2026-11-05T09:00:00Z",
    ...overrides,
  };
}

const DEFAULT_POLICY = policy({
  id: "dp-00000000000000000000000000",
  name: "default",
  is_default: true,
  version: 1,
  description: "Manages nothing. Attach another discovery policy to a catalog, namespace or table to manage its tables.",
  rules: [],
});

function attachment(type: string, path: string[]): ListedTableDiscoveryPolicyAttachmentApiResponse {
  return {
    id: `da-${path.join("-")}`,
    policy_id: "dp-01m7s6c3tqee0rhg00xry2zqqv",
    policy_name: "sales-tables",
    target: { type, path, table_uuid: null },
    orphaned: false,
    attached_at: "2026-11-05T09:00:00Z",
  };
}

function stubApi(
  responses: Record<string, StubHandler> = {},
  saved = policy(),
  attachments: ListedTableDiscoveryPolicyAttachmentApiResponse[] = [],
) {
  return stubCatalogApi({
    [`GET ${PATH}`]: () => jsonResponse(saved),
    "GET /v1/discovery-policies/default": () => jsonResponse(DEFAULT_POLICY),
    "GET /v1/discovery-policies": () => jsonResponse({ policies: [] }),
    [`GET ${PATH}/attachments`]: () => jsonResponse({ attachments }),
    "GET /v1/discovery-policies/default/attachments": () => jsonResponse({ attachments: [] }),
    "GET /v1/scanned-catalogs": () => jsonResponse({ catalogs: [] }),
    ...responses,
  });
}

function renderAt(name = "sales-tables") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/discovery-policies/${name}`]}>
        <Routes>
          <Route path="/discovery-policies/:name" element={<DiscoveryPolicyPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function rulesTable(): HTMLElement {
  return screen.getByRole("table", { name: "Discovery rules, read top to bottom" });
}

function ruleRow(position: number): HTMLElement {
  const row = within(rulesTable()).getAllByRole("row")[position];
  if (row === undefined) throw new Error(`no rule ${position}`);
  return row;
}

// The rules are there; the attachments may still be loading, and the rules' controls must work meanwhile.
async function loaded() {
  await screen.findByRole("table", { name: "Discovery rules, read top to bottom" });
}

function saveButton(): HTMLElement {
  return screen.getByRole("button", { name: "Save" });
}

function discardButton(): HTMLElement {
  return screen.getByRole("button", { name: "Discard changes" });
}

describe("DiscoveryPolicyPage", () => {
  it("names the policy and its version, with links to every version, newest first", async () => {
    stubApi();
    renderAt();
    expect(await screen.findByRole("heading", { level: 1, name: "sales-tables" })).toBeInTheDocument();
    expect(screen.getByText(/^Version 3, saved/)).toBeInTheDocument();
    const links = within(screen.getByRole("navigation", { name: "Versions" })).getAllByRole("link");
    expect(links.map((link) => [link.textContent, link.getAttribute("href")])).toEqual([
      ["v3", "/discovery-policies/sales-tables/versions/3"],
      ["v2", "/discovery-policies/sales-tables/versions/2"],
      ["v1", "/discovery-policies/sales-tables/versions/1"],
    ]);
    const crumbs = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(within(crumbs).getByRole("link", { name: "Discovery policies" })).toHaveAttribute(
      "href",
      "/discovery-policies",
    );
  });

  it("shows the newest 10 versions and the rest behind a button", async () => {
    stubApi({}, policy({ version: 12 }));
    const user = userEvent.setup();
    renderAt();
    await loaded();
    const versions = screen.getByRole("navigation", { name: "Versions" });
    expect(within(versions).getAllByRole("link").map((link) => link.textContent)).toEqual(
      ["v12", "v11", "v10", "v9", "v8", "v7", "v6", "v5", "v4", "v3"],
    );
    await user.click(within(versions).getByRole("button", { name: "Show 2 earlier versions" }));
    expect(within(versions).getAllByRole("link")).toHaveLength(12);
    expect(within(versions).getByRole("link", { name: "v2" })).toHaveFocus();
  });

  it("edits the description, the no-match outcome and the rules", async () => {
    stubApi();
    renderAt();
    await loaded();
    expect(screen.getByRole("textbox", { name: "Description" })).toHaveValue("Sales tables");
    expect(screen.getByRole("combobox", { name: "When no rule matches" })).toHaveTextContent("Do not manage");
    expect(within(ruleRow(1)).getByText("orders*")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add rule" })).toBeEnabled();
  });

  it("enables Save and Discard only while the draft differs", async () => {
    stubApi();
    const user = userEvent.setup();
    renderAt();
    await loaded();
    expect(saveButton()).toBeDisabled();
    expect(discardButton()).toBeDisabled();
    const description = screen.getByRole("textbox", { name: "Description" });
    await user.type(description, "!");
    expect(saveButton()).toBeEnabled();
    expect(discardButton()).toBeEnabled();
    await user.type(description, "{Backspace}");
    expect(saveButton()).toBeDisabled();
    expect(discardButton()).toBeDisabled();
  });

  it("saves the draft with the version it read and says discovery runs", async () => {
    const calls = stubApi({ [`PUT ${PATH}`]: () => jsonResponse(policy({ version: 4 })) });
    const user = userEvent.setup();
    renderAt();
    await loaded();
    await user.click(screen.getByRole("button", { name: "Move rule 2 up" }));
    await user.click(screen.getByRole("combobox", { name: "When no rule matches" }));
    await user.click(await screen.findByRole("option", { name: "Manage" }));
    await user.click(saveButton());

    expect(await screen.findByText("Saved. Discovering tables…")).toBeInTheDocument();
    expect(callsTo(calls, "PUT", PATH).map((call) => call.body)).toEqual([
      {
        version: 3,
        description: "Sales tables",
        no_match_outcome: "manage",
        rules: [policy().rules[1], policy().rules[0]],
      },
    ]);
    expect(callsTo(calls, "GET", PATH).length).toBeGreaterThan(1);
  });

  it("adds a rule, sent without an id", async () => {
    const calls = stubApi({ [`PUT ${PATH}`]: () => jsonResponse(policy({ version: 4 })) });
    const user = userEvent.setup();
    renderAt();
    await loaded();
    await user.click(screen.getByRole("button", { name: "Add rule" }));
    const dialog = await screen.findByRole("dialog", { name: "Add rule" });
    await user.type(within(dialog).getByRole("textbox", { name: "New namespace glob" }), "finance{Enter}");
    await user.click(within(dialog).getByRole("button", { name: "Add rule" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(within(ruleRow(3)).getByText("finance")).toBeInTheDocument();
    await user.click(saveButton());

    await screen.findByText("Saved. Discovering tables…");
    const body = callsTo(calls, "PUT", PATH)[0]?.body as { rules: Record<string, unknown>[] };
    expect(body.rules[2]).toEqual({
      outcome: "manage",
      conditions: [{ attribute: "namespace", operator: "glob", values: ["finance"] }],
    });
  });

  it("edits a rule in the editor", async () => {
    stubApi();
    const user = userEvent.setup();
    renderAt();
    await loaded();
    await user.click(screen.getByRole("button", { name: "Edit rule 2" }));
    const dialog = await screen.findByRole("dialog", { name: "Edit rule" });
    await user.type(within(dialog).getByRole("textbox", { name: "New table name glob" }), "staging_*{Enter}");
    await user.click(within(dialog).getByRole("button", { name: "Update rule" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(within(ruleRow(2)).getByText("staging_*")).toBeInTheDocument();
    expect(saveButton()).toBeEnabled();
  });

  it("deletes a rule of the draft without asking, and Discard brings it back", async () => {
    stubApi();
    const user = userEvent.setup();
    renderAt();
    await loaded();
    await user.click(screen.getByRole("button", { name: "Delete rule 1" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.queryByText("orders*")).not.toBeInTheDocument();
    await user.click(discardButton());
    expect(screen.getByText("orders*")).toBeInTheDocument();
    expect(saveButton()).toBeDisabled();
  });

  it("keeps the draft and its version when someone else saved, and offers Reload", async () => {
    let reads = 0;
    const calls = stubApi({
      [`GET ${PATH}`]: () => {
        reads += 1;
        return jsonResponse(policy({ version: reads === 1 ? 3 : 4 }));
      },
      [`PUT ${PATH}`]: () => jsonResponse({ detail: "policy sales-tables is at version 4, not 3" }, 409),
    });
    const user = userEvent.setup();
    renderAt();
    await loaded();
    await user.click(screen.getByRole("button", { name: "Delete rule 2" }));
    await user.click(saveButton());

    expect(
      await screen.findByText("Someone else changed this policy. Reload to see their version."),
    ).toBeInTheDocument();
    expect(screen.queryByText("tmp_*")).not.toBeInTheDocument();
    await waitFor(() => expect(reads).toBe(2));
    await user.click(saveButton());
    await waitFor(() => expect(callsTo(calls, "PUT", PATH)).toHaveLength(2));
    expect(callsTo(calls, "PUT", PATH).map((call) => (call.body as { version: number }).version)).toEqual([3, 3]);

    await user.click(screen.getByRole("button", { name: "Reload" }));
    expect(await screen.findByText("tmp_*")).toBeInTheDocument();
    expect(screen.getByText(/^Version 4, saved/)).toBeInTheDocument();
    expect(screen.queryByText(/Someone else changed/)).not.toBeInTheDocument();
  });

  it("has nothing to save once an edit is undone, even after a refetch moved the saved version", async () => {
    let reads = 0;
    stubApi({
      [`GET ${PATH}`]: () => {
        reads += 1;
        return jsonResponse(policy({ version: reads === 1 ? 3 : 4 }));
      },
      [`PUT ${PATH}`]: () => jsonResponse({ detail: "policy sales-tables is at version 4, not 3" }, 409),
    });
    const user = userEvent.setup();
    renderAt();
    await loaded();
    const description = screen.getByRole("textbox", { name: "Description" });
    await user.type(description, "!");
    await user.click(saveButton());
    await screen.findByText("Someone else changed this policy. Reload to see their version.");
    await waitFor(() => expect(reads).toBe(2));
    await user.type(description, "{Backspace}");
    expect(saveButton()).toBeDisabled();
    expect(discardButton()).toBeDisabled();
  });

  it("shows the API's detail when the content is refused", async () => {
    stubApi({ [`PUT ${PATH}`]: () => jsonResponse({ detail: "unknown discovery rule id dr-gone" }, 422) });
    const user = userEvent.setup();
    renderAt();
    await loaded();
    await user.type(screen.getByRole("textbox", { name: "Description" }), "!");
    await user.click(saveButton());
    expect(await screen.findByText("unknown discovery rule id dr-gone")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reload" })).not.toBeInTheDocument();
    expect(screen.queryByText("Saved. Discovering tables…")).not.toBeInTheDocument();
  });

  it("shows the default read only, with its fixed description", async () => {
    stubApi();
    renderAt("default");
    expect(await screen.findByRole("heading", { level: 1, name: "default" })).toBeInTheDocument();
    await loaded();
    expect(screen.getByText(DEFAULT_POLICY.description)).toBeInTheDocument();
    expect(screen.getByText("Do not manage")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add rule" })).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("lists where the policy is attached, under its rules", async () => {
    stubApi({}, policy(), [attachment("catalog", ["iceberg"])]);
    renderAt();
    await loaded();
    const attached = screen.getByRole("region", { name: "Attached to" });
    expect(await within(attached).findByRole("link", { name: "iceberg" })).toHaveAttribute("href", "/catalogs/iceberg");
    expect(rulesTable().compareDocumentPosition(attached) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("hints under each rule which conditions cannot tell tables apart where the policy is attached", async () => {
    stubApi({}, policy(), [
      attachment("namespace", ["iceberg", "sales"]),
      attachment("table", ["iceberg", "finance", "ledger"]),
    ]);
    renderAt();
    await loaded();
    const tableHint = "On a table, a rule either always or never matches it.";
    const namespaceHint = "Attached to namespace iceberg.sales: a namespace glob only tells its child namespaces apart.";
    await waitFor(() => expect(within(ruleRow(1)).getByText(namespaceHint)).toBeInTheDocument());
    expect(within(ruleRow(1)).getByText(tableHint)).toBeInTheDocument();
    expect(within(ruleRow(2)).getByText(tableHint)).toBeInTheDocument();
    expect(within(ruleRow(2)).queryByText(namespaceHint)).not.toBeInTheDocument();
  });

  it("hints on a rule of the draft before it is saved", async () => {
    stubApi({}, policy({ rules: [] }), [attachment("namespace", ["iceberg", "sales"])]);
    const user = userEvent.setup();
    renderAt();
    await loaded();
    await screen.findByRole("button", { name: "Detach from iceberg.sales" });
    await user.click(screen.getByRole("button", { name: "Add rule" }));
    const dialog = await screen.findByRole("dialog", { name: "Add rule" });
    await user.type(within(dialog).getByRole("textbox", { name: "New namespace glob" }), "finance{Enter}");
    await user.click(within(dialog).getByRole("button", { name: "Add rule" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(
      within(ruleRow(1)).getByText(
        "Attached to namespace iceberg.sales: a namespace glob only tells its child namespaces apart.",
      ),
    ).toBeInTheDocument();
  });

  it("lets the default be attached too", async () => {
    stubApi();
    renderAt("default");
    await loaded();
    const attached = screen.getByRole("region", { name: "Attached to" });
    expect(
      await within(attached).findByText("Not attached. Attach it to a catalog, namespace or table to apply it."),
    ).toBeInTheDocument();
    expect(within(attached).getByRole("button", { name: "Attach" })).toBeEnabled();
  });

  it("says when the policy cannot be loaded", async () => {
    stubApi({ [`GET ${PATH}`]: () => jsonResponse({ detail: "discovery policy sales-tables not found" }, 404) });
    renderAt();
    expect(
      await screen.findByText("Could not load discovery policy sales-tables: discovery policy sales-tables not found"),
    ).toBeInTheDocument();
  });
});
