import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import type { DiscoveryRuleDraft } from "@/lib/discoveryPolicyDraft";
import { DiscoveryRuleEditor } from "./DiscoveryRuleEditor";

const RULE: DiscoveryRuleDraft = {
  key: "dr-1",
  id: "dr-1",
  outcome: "manage",
  namespaces: ["sales"],
  tableNames: [],
};

function renderEditor(onSubmit = vi.fn(), rule = RULE) {
  render(<DiscoveryRuleEditor title="Edit rule" submitLabel="Update rule" rule={rule} onSubmit={onSubmit} onClose={() => {}} />);
  return { onSubmit, dialog: screen.getByRole("dialog", { name: "Edit rule" }) };
}

// The page's Edit button opens the editor and the editor closes itself; focus must come back.
function Harness() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        Edit rule 1
      </button>
      {open && (
        <DiscoveryRuleEditor
          title="Edit rule"
          submitLabel="Update rule"
          rule={RULE}
          onSubmit={() => setOpen(false)}
          onClose={() => setOpen(false)}
        />
      )}
    </>
  );
}

describe("DiscoveryRuleEditor", () => {
  it("has an Outcome select, Namespace globs and Table name globs", () => {
    const { dialog } = renderEditor();
    expect(within(dialog).getByRole("combobox", { name: "Outcome" })).toHaveTextContent("Manage");
    expect(within(dialog).getByRole("group", { name: "Namespace" })).toBeInTheDocument();
    expect(within(dialog).getByRole("group", { name: "Table name" })).toBeInTheDocument();
    expect(within(dialog).getByRole("textbox", { name: "New namespace glob" })).toBeInTheDocument();
    expect(within(dialog).getByRole("textbox", { name: "New table name glob" })).toBeInTheDocument();
    expect(within(dialog).queryByRole("spinbutton")).not.toBeInTheDocument();
    expect(within(dialog).queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("returns the edited rule", async () => {
    const user = userEvent.setup();
    const { onSubmit, dialog } = renderEditor();
    await user.click(within(dialog).getByRole("combobox", { name: "Outcome" }));
    await user.click(await screen.findByRole("option", { name: "Do not manage" }));
    await user.click(within(dialog).getByRole("button", { name: "Remove namespace glob sales" }));
    await user.type(within(dialog).getByRole("textbox", { name: "New table name glob" }), "tmp_*{Enter}");
    await user.click(within(dialog).getByRole("button", { name: "Update rule" }));
    expect(onSubmit).toHaveBeenCalledWith({ ...RULE, outcome: "unmanage", namespaces: [], tableNames: ["tmp_*"] });
  });

  it("refuses a rule with no condition", async () => {
    const user = userEvent.setup();
    const { onSubmit, dialog } = renderEditor();
    await user.click(within(dialog).getByRole("button", { name: "Remove namespace glob sales" }));
    await user.click(within(dialog).getByRole("button", { name: "Update rule" }));
    expect(within(dialog).getByRole("alert")).toHaveTextContent(
      "A rule needs at least one condition: a namespace or a table name glob.",
    );
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("is reached field by field with Tab", async () => {
    const user = userEvent.setup();
    const { dialog } = renderEditor();
    await waitFor(() => expect(within(dialog).getByRole("button", { name: "Close" })).toHaveFocus());
    const order = [
      within(dialog).getByRole("combobox", { name: "Outcome" }),
      within(dialog).getByRole("button", { name: "Remove namespace glob sales" }),
      within(dialog).getByRole("textbox", { name: "New namespace glob" }),
      within(dialog).getByRole("button", { name: "Add namespace glob" }),
      within(dialog).getByRole("textbox", { name: "New table name glob" }),
      within(dialog).getByRole("button", { name: "Add table name glob" }),
      within(dialog).getByRole("button", { name: "Cancel" }),
      within(dialog).getByRole("button", { name: "Update rule" }),
    ];
    for (const control of order) {
      await user.tab();
      expect(control).toHaveFocus();
    }
  });

  it("closes on Escape and gives focus back to the button that opened it", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const opener = screen.getByRole("button", { name: "Edit rule 1" });
    await user.click(opener);
    await screen.findByRole("dialog", { name: "Edit rule" });
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await waitFor(() => expect(opener).toHaveFocus());
  });
});
