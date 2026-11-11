import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import type {
  PreviewTableDiscoveryRulesApiResponse,
  TableDiscoveryRuleApiResponse,
} from "../api/generated/model";
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

const PREVIEW: PreviewTableDiscoveryRulesApiResponse = {
  tables: [
    { catalog: "iceberg", namespace: "e2e", table: "tm_e2e_orders", rule_id: "r-early", managed: true },
    { catalog: "iceberg", namespace: "retail", table: "customers", rule_id: null, managed: false },
  ],
  managed: 1,
  unmanaged: 1,
};

// Answers requests keyed "METHOD /path"; any other request is a 404.
function stubApi(responses: Record<string, StubHandler> = {}) {
  return stubCatalogApi({
    "GET /v1/discovery-rules": () => jsonResponse({ version: 2, rules: RULES }),
    "POST /v1/discovery-rules/preview": () => jsonResponse(PREVIEW),
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
    await user.click(within(dialog).getByRole("button", { name: "Add rule" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Save" }));

    await screen.findByText("Saved. Discovering tables…");
    const body = callsTo(calls, "PUT", "/v1/discovery-rules")[0]?.body as { rules: Record<string, unknown>[] };
    expect(body.rules.map((r) => r.priority)).toEqual([10, 50, 60]);
    expect(body.rules[2]).not.toHaveProperty("id");
    expect(body.rules[2]).toMatchObject({ action: "include", enabled: true, catalogs: ["*"], namespaces: ["*"], tables: ["*"] });
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

  it("previews the draft and names the rule that decides each table", async () => {
    const calls = stubApi();
    const user = userEvent.setup();
    renderPage();
    const preview = await screen.findByRole("region", { name: "Preview" });
    expect(await within(preview).findByText("1 managed, 1 unmanaged")).toBeInTheDocument();
    const decided = within(preview).getByRole("group", { name: /Priority 10, include/ });
    expect(within(decided).getByText("e2e.tm_e2e_orders")).toBeInTheDocument();
    const undecided = within(preview).getByRole("group", { name: /No rule matches/ });
    expect(within(undecided).getByText("retail.customers")).toBeInTheDocument();

    await user.click(within(ruleRow("50")).getByRole("switch", { name: "Rule 50 enabled" }));
    await waitFor(() => expect(callsTo(calls, "POST", "/v1/discovery-rules/preview")).toHaveLength(2));
    const body = callsTo(calls, "POST", "/v1/discovery-rules/preview")[1]?.body as { rules: Record<string, unknown>[] };
    expect(body.rules.map((r) => [r.id, r.enabled])).toEqual([
      ["r-early", true],
      ["r-late", true],
    ]);
  });

  it("labels the preview by the rules that were sent with it, not the newer draft", async () => {
    // The table goes to the first include rule of the sent list. The answer for a list that
    // starts with an exclude rule is held back until the test releases it.
    let release = () => {};
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    let heldArrived = false;
    stubApi({
      "GET /v1/discovery-rules": () => jsonResponse({ version: 0, rules: [] }),
      "POST /v1/discovery-rules/preview": async (body) => {
        const { rules } = body as { rules: { action: string }[] };
        if (rules[0]?.action === "exclude") {
          heldArrived = true;
          await held;
        }
        const index = rules.findIndex((r) => r.action === "include");
        return jsonResponse({
          tables: [
            { catalog: "iceberg", namespace: "retail", table: "orders", rule_id: index < 0 ? null : `#${index}`, managed: index >= 0 },
          ],
          managed: index < 0 ? 0 : 1,
          unmanaged: index < 0 ? 1 : 0,
        });
      },
    });
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("No discovery rules. No table is managed.");

    await user.click(screen.getByRole("button", { name: "Add rule" }));
    let dialog = await screen.findByRole("dialog", { name: "Add rule" });
    await user.click(within(dialog).getByRole("button", { name: "Add rule" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Add rule" }));
    dialog = await screen.findByRole("dialog", { name: "Add rule" });
    await user.click(within(dialog).getByRole("combobox", { name: "Action" }));
    await user.click(await screen.findByRole("option", { name: "Exclude" }));
    await user.click(within(dialog).getByRole("button", { name: "Add rule" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());

    const preview = screen.getByRole("region", { name: "Preview" });
    const before = "Priority 10, include (unsaved): 1 table, managed";
    expect(await within(preview).findByRole("group", { name: before })).toBeInTheDocument();

    await user.click(within(ruleRow("20")).getByRole("button", { name: "Move rule 20 up" }));
    await waitFor(() => expect(heldArrived).toBe(true));
    // The held answer is not in yet: the tables shown still belong to the list sent before.
    expect(preview).toHaveAttribute("aria-busy", "true");
    expect(within(preview).getByRole("group", { name: before })).toBeInTheDocument();

    release();
    expect(
      await within(preview).findByRole("group", { name: "Priority 20, include (unsaved): 1 table, managed" }),
    ).toBeInTheDocument();
    expect(preview).toHaveAttribute("aria-busy", "false");
  });
});
