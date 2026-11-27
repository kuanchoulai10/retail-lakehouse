import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";
import type {
  ListedTableDiscoveryPolicyAttachmentApiResponse,
  TableDiscoveryPolicyApiResponse,
} from "../api/generated/model";
import { getGetEffectivePoliciesQueryKey, getGetTableEffectivePoliciesQueryKey } from "../api/generated/tables/tables";
import { callsTo, stubCatalogApi, type StubHandler } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { DiscoveryPolicyPage } from "./DiscoveryPolicyPage";

const PATH = "/v1/discovery-policies/sales-tables";

function policy(overrides: Partial<TableDiscoveryPolicyApiResponse> = {}): TableDiscoveryPolicyApiResponse {
  return {
    id: "dp-01m7s6c3tqee0rhg00xry2zqqv",
    name: "sales-tables",
    version: 3,
    description: "Sales tables",
    rules: [
      { action: "include", table_name_pattern: "orders*" },
      { action: "exclude", table_name_pattern: "tmp_*" },
    ],
    created_at: "2026-11-01T09:00:00Z",
    updated_at: "2026-11-05T09:00:00Z",
    ...overrides,
  };
}

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
    "GET /v1/discovery-policies": () => jsonResponse({ policies: [] }),
    [`GET ${PATH}/attachments`]: () => jsonResponse({ attachments }),
    "GET /v1/scanned-catalogs": () => jsonResponse({ catalogs: [] }),
    ...responses,
  });
}

function renderAt(name = "sales-tables") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/discovery-policies/${name}`]}>
        <Routes>
          <Route path="/discovery-policies/:name" element={<DiscoveryPolicyPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return client;
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

function patternField(position: number): HTMLElement {
  return screen.getByRole("textbox", { name: `Table name pattern of rule ${position}` });
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

  it("edits the description and the rules, with no no-match outcome", async () => {
    stubApi();
    renderAt();
    await loaded();
    expect(screen.getByRole("textbox", { name: "Description" })).toHaveValue("Sales tables");
    expect(screen.queryByRole("combobox", { name: "When no rule matches" })).not.toBeInTheDocument();
    expect(within(ruleRow(1)).getByRole("combobox", { name: "Action of rule 1" })).toHaveTextContent("Include");
    expect(patternField(1)).toHaveValue("orders*");
    expect(within(ruleRow(2)).getByRole("combobox", { name: "Action of rule 2" })).toHaveTextContent("Exclude");
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
    await user.click(screen.getByRole("combobox", { name: "Action of rule 2" }));
    await user.click(await screen.findByRole("option", { name: "Exclude" }));
    await waitFor(() => expect(callsTo(calls, "GET", "/v1/scanned-catalogs")).toHaveLength(1));
    await user.click(saveButton());

    expect(await screen.findByText("Saved. Discovering tables…")).toBeInTheDocument();
    // The save can start or stop the scans of the catalogs the policy is attached in.
    await waitFor(() => expect(callsTo(calls, "GET", "/v1/scanned-catalogs")).toHaveLength(2));
    expect(callsTo(calls, "PUT", PATH).map((call) => call.body)).toEqual([
      {
        version: 3,
        description: "Sales tables",
        rules: [
          { action: "exclude", table_name_pattern: "tmp_*" },
          { action: "exclude", table_name_pattern: "orders*" },
        ],
      },
    ]);
    expect(callsTo(calls, "GET", PATH).length).toBeGreaterThan(1);
  });

  it("marks what applies anywhere stale after a save, since the version changed", async () => {
    stubApi({ [`PUT ${PATH}`]: () => jsonResponse(policy({ version: 4 })) });
    const user = userEvent.setup();
    const client = renderAt();
    await loaded();
    const byLocation = getGetEffectivePoliciesQueryKey({ catalog: "iceberg" });
    const byUuid = getGetTableEffectivePoliciesQueryKey("uuid-orders");
    client.setQueryData(byLocation, {});
    client.setQueryData(byUuid, {});
    await user.click(screen.getByRole("button", { name: "Move rule 2 up" }));
    await user.click(saveButton());

    expect(await screen.findByText("Saved. Discovering tables…")).toBeInTheDocument();
    expect(client.getQueryState(byLocation)?.isInvalidated).toBe(true);
    expect(client.getQueryState(byUuid)?.isInvalidated).toBe(true);
  });

  it("adds a rule as include with an empty pattern, focused, and saves it once it has one", async () => {
    const calls = stubApi({ [`PUT ${PATH}`]: () => jsonResponse(policy({ version: 4 })) });
    const user = userEvent.setup();
    renderAt();
    await loaded();
    await user.click(screen.getByRole("button", { name: "Add rule" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(within(ruleRow(3)).getByRole("combobox", { name: "Action of rule 3" })).toHaveTextContent("Include");
    await waitFor(() => expect(patternField(3)).toHaveFocus());
    expect(patternField(3)).toHaveValue("");
    expect(saveButton()).toBeDisabled();
    expect(screen.getByText("Every rule needs a table name pattern before the policy can be saved.")).toBeInTheDocument();
    await user.keyboard("finance_*");
    expect(saveButton()).toBeEnabled();
    expect(screen.queryByText(/Every rule needs a table name pattern/)).not.toBeInTheDocument();
    await user.click(saveButton());

    await screen.findByText("Saved. Discovering tables…");
    const body = callsTo(calls, "PUT", PATH)[0]?.body as { rules: Record<string, unknown>[] };
    expect(body.rules[2]).toEqual({ action: "include", table_name_pattern: "finance_*" });
  });

  it("keeps the pattern field focused while it is typed in", async () => {
    stubApi();
    const user = userEvent.setup();
    renderAt();
    await loaded();
    await user.clear(patternField(2));
    await user.type(patternField(2), "staging_*");
    expect(patternField(2)).toHaveFocus();
    expect(patternField(2)).toHaveValue("staging_*");
    expect(saveButton()).toBeEnabled();
  });

  it("cannot save a policy with no rules", async () => {
    stubApi();
    const user = userEvent.setup();
    renderAt();
    await loaded();
    await user.click(screen.getByRole("button", { name: "Delete rule 1" }));
    await user.click(screen.getByRole("button", { name: "Delete rule 1" }));
    expect(screen.getByText("No rules. A policy needs at least one.")).toBeInTheDocument();
    expect(saveButton()).toBeDisabled();
    expect(discardButton()).toBeEnabled();
  });

  it("deletes a rule of the draft without asking, and Discard brings it back", async () => {
    stubApi();
    const user = userEvent.setup();
    renderAt();
    await loaded();
    await user.click(screen.getByRole("button", { name: "Delete rule 1" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue("orders*")).not.toBeInTheDocument();
    await user.click(discardButton());
    expect(screen.getByDisplayValue("orders*")).toBeInTheDocument();
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
    expect(screen.queryByDisplayValue("tmp_*")).not.toBeInTheDocument();
    await waitFor(() => expect(reads).toBe(2));
    await user.click(saveButton());
    await waitFor(() => expect(callsTo(calls, "PUT", PATH)).toHaveLength(2));
    expect(callsTo(calls, "PUT", PATH).map((call) => (call.body as { version: number }).version)).toEqual([3, 3]);

    await user.click(screen.getByRole("button", { name: "Reload" }));
    expect(await screen.findByDisplayValue("tmp_*")).toBeInTheDocument();
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
    stubApi({ [`PUT ${PATH}`]: () => jsonResponse({ detail: "a discovery policy needs at least one rule" }, 422) });
    const user = userEvent.setup();
    renderAt();
    await loaded();
    await user.type(screen.getByRole("textbox", { name: "Description" }), "!");
    await user.click(saveButton());
    expect(await screen.findByText("a discovery policy needs at least one rule")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reload" })).not.toBeInTheDocument();
    expect(screen.queryByText("Saved. Discovering tables…")).not.toBeInTheDocument();
  });

  it("lists where the policy is attached, under its rules", async () => {
    stubApi({}, policy(), [attachment("catalog", ["iceberg"])]);
    renderAt();
    await loaded();
    const attached = screen.getByRole("region", { name: "Attached to" });
    expect(await within(attached).findByRole("link", { name: "iceberg" })).toHaveAttribute("href", "/catalogs/iceberg");
    expect(rulesTable().compareDocumentPosition(attached) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("says when the policy cannot be loaded", async () => {
    stubApi({ [`GET ${PATH}`]: () => jsonResponse({ detail: "discovery policy sales-tables not found" }, 404) });
    renderAt();
    expect(
      await screen.findByText("Could not load discovery policy sales-tables: discovery policy sales-tables not found"),
    ).toBeInTheDocument();
  });
});
