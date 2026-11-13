import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import type { TableDiscoveryRuleApiResponse } from "../api/generated/model";
import { callsTo, stubCatalogApi, type StubHandler } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { DiscoveryRulesPage } from "./DiscoveryRulesPage";

function rule(overrides: Partial<TableDiscoveryRuleApiResponse>): TableDiscoveryRuleApiResponse {
  return {
    id: "rule",
    priority: 10,
    action: "include",
    catalogs: ["iceberg"],
    namespaces: ["e2e"],
    tables: ["tm_e2e_*"],
    enabled: true,
    created_at: "2026-11-04T13:07:46Z",
    updated_at: "2026-11-04T13:07:46Z",
    ...overrides,
  };
}

const RULES = [
  rule({ id: "r-late", priority: 50, action: "exclude", namespaces: ["*"], tables: ["tmp_*", "staging_*"], enabled: false }),
  rule({ id: "r-early", priority: 10 }),
];

// Answers requests keyed "METHOD /path"; any other request is a 404.
function stubApi(responses: Record<string, StubHandler> = {}) {
  return stubCatalogApi({
    "GET /v1/discovery-rules": () => jsonResponse({ version: 2, rules: RULES }),
    ...responses,
    "GET *": () => jsonResponse({ detail: "not found" }, 404),
  });
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <DiscoveryRulesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function rulesTable(): HTMLElement {
  return screen.getByRole("table", { name: "Discovery rules in evaluation order" });
}

function ruleRow(priority: string): HTMLElement {
  const row = within(rulesTable())
    .getAllByRole("row")
    .find((r) => within(r).queryAllByRole("cell")[0]?.textContent === priority);
  if (row === undefined) throw new Error(`no rule with priority ${priority}`);
  return row;
}

async function editPriority(user: ReturnType<typeof userEvent.setup>, from: string, to: string) {
  await user.click(within(ruleRow(from)).getByRole("button", { name: `Edit rule ${from}` }));
  const dialog = await screen.findByRole("dialog", { name: "Edit rule" });
  const priority = within(dialog).getByRole("spinbutton", { name: "Priority" });
  await user.clear(priority);
  await user.type(priority, to);
  await user.click(within(dialog).getByRole("button", { name: "Update rule" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
}

async function fillGlobs(
  user: ReturnType<typeof userEvent.setup>,
  dialog: HTMLElement,
  globs: { catalogs: string; namespaces: string; tables: string },
) {
  for (const [field, glob] of Object.entries(globs)) {
    await user.type(within(dialog).getByRole("textbox", { name: `New ${field} glob` }), `${glob}{Enter}`);
  }
}

describe("DiscoveryRulesPage", () => {
  it("lists rules by priority, lowest first", async () => {
    stubApi();
    renderPage();
    await screen.findByText("tm_e2e_*");
    const priorities = within(rulesTable())
      .getAllByRole("row")
      .slice(1)
      .map((row) => within(row).getAllByRole("cell")[0]?.textContent);
    expect(priorities).toEqual(["10", "50"]);
  });

  it("shows the globs, action and state of each rule", async () => {
    stubApi();
    renderPage();
    await screen.findByText("tm_e2e_*");
    const include = ruleRow("10");
    expect(within(include).getByText("Include")).toBeInTheDocument();
    expect(within(include).getByText("e2e")).toBeInTheDocument();
    expect(within(include).getByRole("switch", { name: "Rule 10 enabled" })).toBeChecked();
    const exclude = ruleRow("50");
    expect(within(exclude).getByText("Exclude")).toBeInTheDocument();
    expect(within(exclude).getByText("tmp_*")).toBeInTheDocument();
    expect(within(exclude).getByText("staging_*")).toBeInTheDocument();
    expect(within(exclude).getByRole("switch", { name: "Rule 50 enabled" })).not.toBeChecked();
  });

  it("has no discovery switch", async () => {
    stubApi();
    renderPage();
    await screen.findByText("tm_e2e_*");
    expect(screen.queryByText(/Discovery is (on|off)/)).not.toBeInTheDocument();
    expect(screen.queryByRole("switch", { name: /discovery/i })).not.toBeInTheDocument();
  });

  it("shows an error when the rules cannot be loaded", async () => {
    stubApi({ "GET /v1/discovery-rules": () => jsonResponse({ detail: "boom" }, 500) });
    renderPage();
    expect(await screen.findByText(/Could not load discovery rules: boom/)).toBeInTheDocument();
  });

  it("saves the edited list with one PUT carrying the version it read", async () => {
    const calls = stubApi({
      "PUT /v1/discovery-rules": () => jsonResponse({ version: 3, rules: RULES }),
    });
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("tm_e2e_*");
    await editPriority(user, "50", "5");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Saved. Discovering tables…")).toBeInTheDocument();
    const puts = callsTo(calls, "PUT", "/v1/discovery-rules");
    expect(puts).toHaveLength(1);
    expect(puts[0]?.body).toEqual({
      version: 2,
      rules: [
        {
          id: "r-late",
          priority: 5,
          action: "exclude",
          enabled: false,
          catalogs: ["iceberg"],
          namespaces: ["*"],
          tables: ["tmp_*", "staging_*"],
        },
        {
          id: "r-early",
          priority: 10,
          action: "include",
          enabled: true,
          catalogs: ["iceberg"],
          namespaces: ["e2e"],
          tables: ["tm_e2e_*"],
        },
      ],
    });
  });

  it("sends a new rule without an id", async () => {
    const calls = stubApi({
      "PUT /v1/discovery-rules": () => jsonResponse({ version: 3, rules: RULES }),
    });
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("tm_e2e_*");
    await user.click(screen.getByRole("button", { name: "Add rule" }));
    const dialog = await screen.findByRole("dialog", { name: "Add rule" });
    await fillGlobs(user, dialog, { catalogs: "iceberg", namespaces: "e2e", tables: "new_*" });
    await user.click(within(dialog).getByRole("button", { name: "Add rule" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Save" }));

    await screen.findByText("Saved. Discovering tables…");
    const body = callsTo(calls, "PUT", "/v1/discovery-rules")[0]?.body as { rules: Record<string, unknown>[] };
    expect(body.rules.map((r) => r.priority)).toEqual([10, 50, 60]);
    expect(body.rules[2]).not.toHaveProperty("id");
    expect(body.rules[2]).toMatchObject({
      action: "include",
      enabled: true,
      catalogs: ["iceberg"],
      namespaces: ["e2e"],
      tables: ["new_*"],
    });
  });

  it("opens a new rule with every glob list empty", async () => {
    stubApi();
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("tm_e2e_*");
    await user.click(screen.getByRole("button", { name: "Add rule" }));
    const dialog = await screen.findByRole("dialog", { name: "Add rule" });
    expect(within(dialog).queryByText("*")).not.toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Add rule" }));
    expect(await within(dialog).findByText("Add at least one catalog glob.")).toBeInTheDocument();
  });

  it("shows the API's message inline when a priority is taken twice", async () => {
    stubApi({
      "PUT /v1/discovery-rules": () => jsonResponse({ detail: "Two rules share priority 10" }, 422),
    });
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("tm_e2e_*");
    await editPriority(user, "50", "10");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Two rules share priority 10");
    expect(screen.queryByText("Saved. Discovering tables…")).not.toBeInTheDocument();
  });

  it("keeps the draft when someone else changed the rules", async () => {
    stubApi({
      "PUT /v1/discovery-rules": () => jsonResponse({ detail: "stale version" }, 409),
    });
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("tm_e2e_*");
    await editPriority(user, "50", "5");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Someone else changed these rules. Reload to see their version.")).toBeInTheDocument();
    expect(ruleRow("5")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reload" })).toBeInTheDocument();
  });

  it("restores the saved list on Discard changes", async () => {
    stubApi();
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("tm_e2e_*");
    await user.click(within(ruleRow("10")).getByRole("button", { name: "Delete rule 10" }));
    expect(screen.queryByText("tm_e2e_*")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Discard changes" }));
    expect(screen.getByText("tm_e2e_*")).toBeInTheDocument();
  });

  it("moves a rule up by trading priorities with the one above", async () => {
    const calls = stubApi({
      "PUT /v1/discovery-rules": () => jsonResponse({ version: 3, rules: RULES }),
    });
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("tm_e2e_*");
    await user.click(within(ruleRow("50")).getByRole("button", { name: "Move rule 50 up" }));
    await user.click(screen.getByRole("button", { name: "Save" }));

    await screen.findByText("Saved. Discovering tables…");
    const body = callsTo(calls, "PUT", "/v1/discovery-rules")[0]?.body as { rules: Record<string, unknown>[] };
    expect(body.rules.map((r) => [r.id, r.priority])).toEqual([
      ["r-late", 10],
      ["r-early", 50],
    ]);
  });

  it("shows no Preview and sends no preview request", async () => {
    const calls = stubApi();
    renderPage();
    await screen.findByText("tm_e2e_*");
    await new Promise((resolve) => setTimeout(resolve, 500));

    expect(screen.queryByRole("region", { name: "Preview" })).not.toBeInTheDocument();
    expect(callsTo(calls, "POST", "/v1/discovery-rules/preview")).toHaveLength(0);
  });
});
