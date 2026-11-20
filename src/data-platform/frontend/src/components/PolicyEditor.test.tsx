import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { bodyOf, callsTo, stubCatalogApi, type StubbedCall } from "../test/catalogApiStub";
import { jsonResponse, policyContentFixture, policyFixture } from "../test/fixtures";
import { PolicyEditor } from "./PolicyEditor";

const NIGHTLY = policyFixture({ name: "nightly", description: "Nightly compaction", version: 4 });

// What the editor sent (writes only).
function writesOf(calls: StubbedCall[]): StubbedCall[] {
  return calls.filter((call) => call.method !== "GET");
}

function renderEditor(element: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{element}</MemoryRouter>
    </QueryClientProvider>,
  );
}

function section(name: string): HTMLElement {
  return screen.getByRole("group", { name });
}

async function replace(user: ReturnType<typeof userEvent.setup>, field: HTMLElement, value: string) {
  await user.clear(field);
  if (value !== "") await user.type(field, value);
}

describe("PolicyEditor", () => {
  it("creates a policy with its full content and no priority", async () => {
    const calls = stubCatalogApi({
      "POST /v1/maintenance-policies": () => jsonResponse(policyFixture({ name: "weekly", version: 1 }), 201),
    });
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderEditor(<PolicyEditor content={policyContentFixture()} onClose={onClose} />);
    const dialog = await screen.findByRole("dialog", { name: "New policy" });
    await user.type(within(dialog).getByRole("textbox", { name: "Name" }), "weekly");
    await replace(user, within(dialog).getByRole("textbox", { name: "Description" }), "Weekly tidy-up");
    await replace(user, within(dialog).getByRole("textbox", { name: "Check every (seconds)" }), "7200");
    await user.click(within(dialog).getByRole("switch", { name: "Check after catalog commits" }));
    await user.click(within(dialog).getByRole("switch", { name: "Dry run" }));
    await user.click(within(dialog).getByRole("button", { name: "Create policy" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    const body = bodyOf(calls, "POST", "/v1/maintenance-policies");
    expect(body).toEqual({
      ...policyContentFixture(),
      name: "weekly",
      description: "Weekly tidy-up",
      on: { schedule: { every_seconds: 7200 }, catalog_commit: null },
      dry_run: true,
    });
    expect(body).not.toHaveProperty("priority");
  });

  it("sends an operation taken out of the policy as null, with the version it read", async () => {
    const calls = stubCatalogApi({
      "PUT /v1/maintenance-policies/nightly": () => jsonResponse({ ...NIGHTLY, version: 5 }),
    });
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderEditor(<PolicyEditor policy={NIGHTLY} content={NIGHTLY} onClose={onClose} />);
    const dialog = await screen.findByRole("dialog", { name: "Edit policy" });
    expect(within(dialog).queryByRole("textbox", { name: "Name" })).not.toBeInTheDocument();
    await user.click(within(section("Expire snapshots")).getByRole("switch", { name: "In this policy" }));
    await user.click(within(dialog).getByRole("button", { name: "Save" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(bodyOf(calls, "PUT", "/v1/maintenance-policies/nightly")).toEqual({
      ...policyContentFixture(),
      description: "Nightly compaction",
      expire_snapshots: null,
      version: 4,
    });
  });

  it("sends the options chosen and leaves one set back to the procedure default out", async () => {
    const calls = stubCatalogApi({
      "PUT /v1/maintenance-policies/nightly": () => jsonResponse({ ...NIGHTLY, version: 5 }),
    });
    const user = userEvent.setup();
    renderEditor(<PolicyEditor policy={NIGHTLY} content={NIGHTLY} onClose={vi.fn()} />);
    const rewrite = section("Rewrite data files");
    expect(within(rewrite).getByRole("combobox", { name: "Partial progress" })).toHaveTextContent("On");
    await user.click(within(rewrite).getByRole("combobox", { name: "Partial progress" }));
    await user.click(await screen.findByRole("option", { name: "Procedure default" }));
    await user.click(within(rewrite).getByRole("combobox", { name: "Rewrite all" }));
    await user.click(await screen.findByRole("option", { name: "On" }));
    await replace(user, within(section("Rewrite manifests")).getByRole("textbox", { name: "Small manifests at most" }), "8");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(callsTo(calls, "PUT", "/v1/maintenance-policies/nightly")).toHaveLength(1));
    const body = bodyOf(calls, "PUT", "/v1/maintenance-policies/nightly") as ReturnType<typeof policyContentFixture>;
    expect(body.rewrite_data_files?.options).toEqual({ min_input_files: 2, rewrite_all: true });
    expect(body.rewrite_manifests).toEqual({ target: { small_manifests: { at_most: 8 } }, options: null });
  });

  it("shows the API's refusal of a value in the dialog", async () => {
    stubCatalogApi({
      "PUT /v1/maintenance-policies/nightly": () =>
        jsonResponse({ detail: "expire_snapshots.target.min_snapshots_to_keep must be at least 1" }, 422),
    });
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderEditor(<PolicyEditor policy={NIGHTLY} content={NIGHTLY} onClose={onClose} />);
    await replace(user, within(section("Expire snapshots")).getByRole("textbox", { name: "Min snapshots to keep" }), "0");
    await user.click(screen.getByRole("button", { name: "Save" }));
    const dialog = screen.getByRole("dialog", { name: "Edit policy" });
    expect(
      await within(dialog).findByText("expire_snapshots.target.min_snapshots_to_keep must be at least 1"),
    ).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("shows the conflict copy on a stale version and reloads their version", async () => {
    const theirs = { ...NIGHTLY, version: 6, on: { schedule: { every_seconds: 600 }, catalog_commit: null } };
    const calls = stubCatalogApi({
      "PUT /v1/maintenance-policies/nightly": () => jsonResponse({ detail: "stale version" }, 409),
      "GET /v1/maintenance-policies/nightly": () => jsonResponse(theirs),
    });
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderEditor(<PolicyEditor policy={NIGHTLY} content={NIGHTLY} onClose={onClose} />);
    await user.click(await screen.findByRole("button", { name: "Save" }));

    expect(
      await screen.findByText("Someone else changed this policy. Reload to see their version."),
    ).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Reload" }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Check every (seconds)" })).toHaveValue("600"));
    expect(screen.getByRole("switch", { name: "Check after catalog commits" })).not.toBeChecked();
    expect(screen.queryByText(/Someone else changed this policy/)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(callsTo(calls, "PUT", "/v1/maintenance-policies/nightly")).toHaveLength(2));
    expect(callsTo(calls, "PUT", "/v1/maintenance-policies/nightly")[1]?.body).toMatchObject({ version: 6 });
  });

  it("shows the API's message when a save is refused", async () => {
    stubCatalogApi({
      "POST /v1/maintenance-policies": () => jsonResponse({ detail: "policy weekly already exists" }, 409),
    });
    const user = userEvent.setup();
    renderEditor(<PolicyEditor content={policyContentFixture()} onClose={vi.fn()} />);
    await user.type(await screen.findByRole("textbox", { name: "Name" }), "weekly");
    await user.click(screen.getByRole("button", { name: "Create policy" }));
    expect(await screen.findByText("policy weekly already exists")).toBeInTheDocument();
  });

  it("refuses a name the API would refuse, without sending it", async () => {
    const calls = stubCatalogApi({});
    const user = userEvent.setup();
    renderEditor(<PolicyEditor content={policyContentFixture()} onClose={vi.fn()} />);
    await user.type(await screen.findByRole("textbox", { name: "Name" }), "nightly policy");
    await user.click(screen.getByRole("button", { name: "Create policy" }));
    expect(
      screen.getByText("A name uses letters, digits, - and _ only, at most 64 characters."),
    ).toBeInTheDocument();
    expect(writesOf(calls)).toEqual([]);
  });

  it("refuses a check interval under a minute, without sending it", async () => {
    const calls = stubCatalogApi({});
    const user = userEvent.setup();
    renderEditor(<PolicyEditor policy={NIGHTLY} content={NIGHTLY} onClose={vi.fn()} />);
    await replace(user, screen.getByRole("textbox", { name: "Check every (seconds)" }), "30");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(screen.getByText("Check every must be 60 to 604800 seconds.")).toBeInTheDocument();
    expect(writesOf(calls)).toEqual([]);
  });

  it("refuses a value that is not a whole number, naming the section and the field", async () => {
    const calls = stubCatalogApi({});
    const user = userEvent.setup();
    renderEditor(<PolicyEditor policy={NIGHTLY} content={NIGHTLY} onClose={vi.fn()} />);
    await replace(user, within(section("Expire snapshots")).getByRole("textbox", { name: "Min snapshots to keep" }), "1e");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(screen.getByText("Expire snapshots: Min snapshots to keep must be a whole number.")).toBeInTheDocument();
    expect(writesOf(calls)).toEqual([]);
  });

  it("shows each operation with a target and an options group, and no priority", () => {
    stubCatalogApi({});
    renderEditor(<PolicyEditor policy={NIGHTLY} content={NIGHTLY} onClose={vi.fn()} />);
    for (const name of ["Rewrite data files", "Rewrite manifests", "Expire snapshots", "Remove orphan files"]) {
      expect(within(section(name)).getByRole("group", { name: "Target" })).toBeInTheDocument();
      expect(within(section(name)).getByRole("group", { name: "Options" })).toBeInTheDocument();
    }
    expect(within(section("Rewrite data files")).getByRole("combobox", { name: "Per" })).toHaveTextContent(
      "Each partition",
    );
    expect(screen.queryByRole("combobox", { name: "Priority" })).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: /Cooldown/ })).not.toBeInTheDocument();
  });

  it("points to the platform settings for cooldowns and failure back-off", () => {
    stubCatalogApi({});
    renderEditor(<PolicyEditor policy={NIGHTLY} content={NIGHTLY} onClose={vi.fn()} />);
    expect(screen.getByRole("link", { name: "platform settings" })).toHaveAttribute("href", "/platform-settings");
  });

  it("is operated with the keyboard", async () => {
    stubCatalogApi({});
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderEditor(<PolicyEditor policy={NIGHTLY} content={NIGHTLY} onClose={onClose} />);
    const dialog = await screen.findByRole("dialog", { name: "Edit policy" });
    within(dialog).getByRole("textbox", { name: "Description" }).focus();
    await user.tab();
    expect(within(dialog).getByRole("textbox", { name: "Check every (seconds)" })).toHaveFocus();

    await user.tab();
    const commits = within(dialog).getByRole("switch", { name: "Check after catalog commits" });
    expect(commits).toHaveFocus();
    await user.keyboard(" ");
    expect(commits).not.toBeChecked();
    expect(within(dialog).queryByRole("textbox", { name: "Debounce (seconds)" })).not.toBeInTheDocument();
    await user.keyboard(" ");
    expect(within(dialog).getByRole("textbox", { name: "Debounce (seconds)" })).toHaveValue("300");

    const expire = section("Expire snapshots");
    const included = within(expire).getByRole("switch", { name: "In this policy" });
    included.focus();
    await user.keyboard(" ");
    expect(within(expire).queryByRole("textbox", { name: "Min snapshots to keep" })).not.toBeInTheDocument();
    await user.keyboard(" ");
    expect(within(expire).getByRole("textbox", { name: "Min snapshots to keep" })).toHaveValue("10");

    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });
});
