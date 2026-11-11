import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { DiscoveryRuleDraft } from "@/lib/discoveryRuleDraft";
import { DiscoveryRuleEditor } from "./DiscoveryRuleEditor";

const RULE: DiscoveryRuleDraft = {
  key: "r1",
  id: "r1",
  priority: 10,
  action: "include",
  enabled: true,
  catalogs: ["iceberg"],
  namespaces: ["prod.*"],
  tables: ["*"],
};

function renderEditor(onSubmit = vi.fn()) {
  render(<DiscoveryRuleEditor title="Edit rule" submitLabel="Update rule" rule={RULE} onSubmit={onSubmit} onClose={() => {}} />);
  return { onSubmit, dialog: screen.getByRole("dialog", { name: "Edit rule" }) };
}

describe("DiscoveryRuleEditor", () => {
  it("returns the edited rule", async () => {
    const user = userEvent.setup();
    const { onSubmit, dialog } = renderEditor();
    const priority = within(dialog).getByRole("spinbutton", { name: "Priority" });
    await user.clear(priority);
    await user.type(priority, "20");
    await user.click(within(dialog).getByRole("combobox", { name: "Action" }));
    await user.click(await screen.findByRole("option", { name: "Exclude" }));
    await user.click(within(dialog).getByRole("checkbox", { name: "Enabled" }));
    await user.type(within(dialog).getByRole("textbox", { name: "New tables glob" }), "tmp_*{Enter}");
    await user.click(within(dialog).getByRole("button", { name: "Remove tables glob *" }));
    await user.click(within(dialog).getByRole("button", { name: "Update rule" }));
    expect(onSubmit).toHaveBeenCalledWith({ ...RULE, priority: 20, action: "exclude", enabled: false, tables: ["tmp_*"] });
  });

  it("refuses a priority that is not a whole number", async () => {
    const user = userEvent.setup();
    const { onSubmit, dialog } = renderEditor();
    await user.clear(within(dialog).getByRole("spinbutton", { name: "Priority" }));
    await user.click(within(dialog).getByRole("button", { name: "Update rule" }));
    expect(within(dialog).getByRole("alert")).toHaveTextContent("Priority must be a whole number.");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("refuses an empty glob list", async () => {
    const user = userEvent.setup();
    const { onSubmit, dialog } = renderEditor();
    await user.click(within(dialog).getByRole("button", { name: "Remove namespaces glob prod.*" }));
    await user.click(within(dialog).getByRole("button", { name: "Update rule" }));
    expect(within(dialog).getByRole("alert")).toHaveTextContent("Add at least one namespace glob.");
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
