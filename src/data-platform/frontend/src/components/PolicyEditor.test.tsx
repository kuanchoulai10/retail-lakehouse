import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { bodyOf, callsTo, stubCatalogApi, type StubbedCall } from "../test/catalogApiStub";
import { jsonResponse, policyContentFixture, policyFixture } from "../test/fixtures";
import { PolicyEditor } from "./PolicyEditor";

const NIGHTLY = policyFixture({ name: "nightly", description: "Nightly compaction", version: 4 });

// What the editor sent; the scheduler settings it reads for the priority labels do not count.
function writesOf(calls: StubbedCall[]): StubbedCall[] {
  return calls.filter((call) => call.method !== "GET");
}

function renderEditor(element: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{element}</QueryClientProvider>);
}

function section(name: string): HTMLElement {
  return screen.getByRole("group", { name });
}

async function replace(user: ReturnType<typeof userEvent.setup>, field: HTMLElement, value: string) {
  await user.clear(field);
  if (value !== "") await user.type(field, value);
}

describe("PolicyEditor", () => {
  it("creates a policy with its full content", async () => {
    const calls = stubCatalogApi({
      "POST /v1/maintenance-policies": () => jsonResponse(policyFixture({ name: "weekly", version: 1 }), 201),
    });
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderEditor(<PolicyEditor content={policyContentFixture()} onClose={onClose} />);
    const dialog = await screen.findByRole("dialog", { name: "New policy" });
    await user.type(within(dialog).getByRole("textbox", { name: "Name" }), "weekly");
    await replace(user, within(dialog).getByRole("textbox", { name: "Description" }), "Weekly tidy-up");
    await replace(user, within(dialog).getByRole("textbox", { name: "Reconcile interval (seconds)" }), "7200");
    await user.click(within(dialog).getByRole("switch", { name: "Dry run" }));
    const expire = section("Expire snapshots");
    await replace(user, within(expire).getByRole("textbox", { name: "Retain last" }), "3");
    await user.click(within(section("Remove orphan files")).getByRole("switch", { name: "Enabled" }));
    await user.click(within(dialog).getByRole("button", { name: "Create policy" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    const expected = policyContentFixture();
    expected.operations.expire_snapshots.execution_policy.retain_last = 3;
    expected.operations.remove_orphan_files.enabled = false;
    expect(bodyOf(calls, "POST", "/v1/maintenance-policies")).toEqual({
      ...expected,
      name: "weekly",
      description: "Weekly tidy-up",
      reconcile_interval_seconds: 7200,
      dry_run: true,
    });
  });

  it("sends a condition left empty as not checked and optional values left empty as null", async () => {
    const calls = stubCatalogApi({
      "PUT /v1/maintenance-policies/nightly": () => jsonResponse({ ...NIGHTLY, version: 5 }),
    });
    const user = userEvent.setup();
    renderEditor(<PolicyEditor policy={NIGHTLY} content={NIGHTLY} onClose={vi.fn()} />);
    const rewrite = section("Rewrite data files");
    await replace(user, within(rewrite).getByRole("textbox", { name: "Reducible files at least" }), "");
    await replace(user, within(rewrite).getByRole("textbox", { name: "Target file size (bytes)" }), "134217728");
    const manifests = section("Rewrite manifests");
    await replace(user, within(manifests).getByRole("textbox", { name: "Smaller than (bytes)" }), "8388608");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(callsTo(calls, "PUT", "/v1/maintenance-policies/nightly")).toHaveLength(1));
    const body = bodyOf(calls, "PUT", "/v1/maintenance-policies/nightly") as {
      operations: ReturnType<typeof policyContentFixture>["operations"];
    };
    expect(body.operations.rewrite_data_files.trigger_policy.conditions).toEqual({ reducible_files: null });
    expect(body.operations.rewrite_data_files.execution_policy.target_file_size_bytes).toBe(134217728);
    expect(body.operations.rewrite_manifests.trigger_policy.conditions).toEqual({
      small_manifests: { at_least: 5, smaller_than_bytes: 8388608 },
    });
  });

  it("sends the version it read when saving an edit", async () => {
    const calls = stubCatalogApi({
      "PUT /v1/maintenance-policies/nightly": () => jsonResponse({ ...NIGHTLY, version: 5 }),
    });
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderEditor(<PolicyEditor policy={NIGHTLY} content={NIGHTLY} onClose={onClose} />);
    const dialog = await screen.findByRole("dialog", { name: "Edit policy" });
    expect(within(dialog).queryByRole("textbox", { name: "Name" })).not.toBeInTheDocument();
    await user.click(within(section("Rewrite manifests")).getByRole("switch", { name: "Enabled" }));
    await user.click(within(dialog).getByRole("button", { name: "Save" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    const content = policyContentFixture();
    content.operations.rewrite_manifests.enabled = false;
    expect(bodyOf(calls, "PUT", "/v1/maintenance-policies/nightly")).toEqual({
      ...content,
      description: "Nightly compaction",
      version: 4,
    });
  });

  it("shows the conflict copy on a stale version and reloads their version", async () => {
    const theirs = { ...NIGHTLY, version: 6, reconcile_interval_seconds: 600 };
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
    await waitFor(() =>
      expect(screen.getByRole("textbox", { name: "Reconcile interval (seconds)" })).toHaveValue("600"),
    );
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

  it("refuses a value that is not a whole number, naming the field", async () => {
    const calls = stubCatalogApi({});
    const user = userEvent.setup();
    renderEditor(<PolicyEditor policy={NIGHTLY} content={NIGHTLY} onClose={vi.fn()} />);
    await replace(user, within(section("Expire snapshots")).getByRole("textbox", { name: "Retain last" }), "");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(screen.getByText("Expire snapshots: Retain last must be a whole number.")).toBeInTheDocument();
    expect(writesOf(calls)).toEqual([]);
  });

  it("refuses a reconcile interval of zero, without sending it", async () => {
    const calls = stubCatalogApi({});
    const user = userEvent.setup();
    renderEditor(<PolicyEditor policy={NIGHTLY} content={NIGHTLY} onClose={vi.fn()} />);
    await replace(user, screen.getByRole("textbox", { name: "Reconcile interval (seconds)" }), "0");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(screen.getByText("Reconcile interval must be greater than zero.")).toBeInTheDocument();
    expect(writesOf(calls)).toEqual([]);
  });

  it("refuses a negative cooldown, without sending it", async () => {
    const calls = stubCatalogApi({});
    const user = userEvent.setup();
    renderEditor(<PolicyEditor policy={NIGHTLY} content={NIGHTLY} onClose={vi.fn()} />);
    await replace(user, within(section("Expire snapshots")).getByRole("textbox", { name: "Cooldown (seconds)" }), "-60");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(screen.getByText("Expire snapshots: Cooldown must be a whole number.")).toBeInTheDocument();
    expect(writesOf(calls)).toEqual([]);
  });

  it("refuses a half-typed optional threshold instead of sending it as not checked", async () => {
    const calls = stubCatalogApi({});
    const user = userEvent.setup();
    renderEditor(<PolicyEditor policy={NIGHTLY} content={NIGHTLY} onClose={vi.fn()} />);
    const reducible = within(section("Rewrite data files")).getByLabelText("Reducible files at least");
    await replace(user, reducible, "1e");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(
      screen.getByText("Rewrite data files: Reducible files at least must be a whole number."),
    ).toBeInTheDocument();
    expect(writesOf(calls)).toEqual([]);
  });

  it("shows each operation with its scope only on rewrite data files", () => {
    stubCatalogApi({});
    renderEditor(<PolicyEditor policy={NIGHTLY} content={NIGHTLY} onClose={vi.fn()} />);
    for (const name of ["Rewrite data files", "Rewrite manifests", "Expire snapshots", "Remove orphan files"]) {
      expect(within(section(name)).getByRole("group", { name: "Trigger" })).toBeInTheDocument();
      expect(within(section(name)).getByRole("group", { name: "Execution" })).toBeInTheDocument();
    }
    expect(within(section("Rewrite data files")).getByRole("combobox", { name: "Scope" })).toBeInTheDocument();
    expect(within(section("Expire snapshots")).queryByRole("combobox", { name: "Scope" })).not.toBeInTheDocument();
  });

  it("sends the priority chosen", async () => {
    const calls = stubCatalogApi({
      "PUT /v1/maintenance-policies/nightly": () => jsonResponse({ ...NIGHTLY, version: 5, priority: "P0" }),
    });
    const user = userEvent.setup();
    renderEditor(<PolicyEditor policy={NIGHTLY} content={NIGHTLY} onClose={vi.fn()} />);
    const dialog = await screen.findByRole("dialog", { name: "Edit policy" });
    await user.click(within(dialog).getByRole("combobox", { name: "Priority" }));
    await user.click(await screen.findByRole("option", { name: "P0" }));
    await user.click(within(dialog).getByRole("button", { name: "Save" }));

    await waitFor(() => expect(callsTo(calls, "PUT", "/v1/maintenance-policies/nightly")).toHaveLength(1));
    expect(bodyOf(calls, "PUT", "/v1/maintenance-policies/nightly")).toMatchObject({ priority: "P0", version: 4 });
  });

  it("offers each priority as it is and says compaction rounds no longer order maintenance", async () => {
    stubCatalogApi({});
    const user = userEvent.setup();
    renderEditor(<PolicyEditor policy={NIGHTLY} content={NIGHTLY} onClose={vi.fn()} />);
    const dialog = await screen.findByRole("dialog", { name: "Edit policy" });
    expect(within(dialog).getByRole("combobox", { name: "Priority" })).toHaveTextContent("P2");
    await user.click(within(dialog).getByRole("combobox", { name: "Priority" }));
    expect(await screen.findByRole("option", { name: "P0" })).toBeInTheDocument();
    expect(
      within(dialog).getByText(
        "Compaction rounds are gone: this priority no longer orders maintenance. A table's own priority (on its Overview tab) does. KCL-91 removes this field.",
      ),
    ).toBeInTheDocument();
  });

  it("starts a policy without a priority at P2", () => {
    stubCatalogApi({});
    const content = policyContentFixture();
    delete content.priority;
    renderEditor(<PolicyEditor content={content} onClose={vi.fn()} />);
    expect(screen.getByRole("combobox", { name: "Priority" })).toHaveTextContent("P2");
  });
});
