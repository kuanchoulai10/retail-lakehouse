import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, screen, userEvent, waitFor, within } from "storybook/test";
import type { DiscoveryRuleDraft } from "@/lib/discoveryPolicyDraft";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { PHONE } from "@/stories/phone";
import { DiscoveryRuleEditor } from "./DiscoveryRuleEditor";

const RULE_ID = "dr-01m7s6c3tqee0rhg00xz1dk9cs";

const RULE: DiscoveryRuleDraft = {
  key: RULE_ID,
  id: RULE_ID,
  outcome: "unmanage",
  namespaces: [],
  tableNames: ["tmp_*", "staging_*"],
};

const meta = {
  title: "Components/Discovery rule editor",
  component: DiscoveryRuleEditor,
  args: { title: "Edit rule", submitLabel: "Update rule", rule: RULE, onSubmit: fn(), onClose: fn() },
} satisfies Meta<typeof DiscoveryRuleEditor>;

export default meta;
type Story = StoryObj<typeof meta>;

function dialog(): HTMLElement {
  return screen.getByRole("dialog", { name: "Edit rule" });
}

export const Edit: Story = {
  play: async ({ args }) => {
    await screen.findByRole("dialog", { name: "Edit rule" });
    await userEvent.type(within(dialog()).getByRole("textbox", { name: "New table name glob" }), "scratch_*{Enter}");
    await userEvent.click(within(dialog()).getByRole("button", { name: "Update rule" }));
    await expect(args.onSubmit).toHaveBeenCalledWith({ ...RULE, tableNames: ["tmp_*", "staging_*", "scratch_*"] });
  },
};

export const Add: Story = {
  args: { title: "Add rule", submitLabel: "Add rule", rule: { key: "new-1", id: null, outcome: "manage", namespaces: [], tableNames: [] } },
  play: async () => {
    const added = await screen.findByRole("dialog", { name: "Add rule" });
    await expect(within(added).getByRole("combobox", { name: "Outcome" })).toHaveTextContent("Manage");
  },
};

export const NoCondition: Story = {
  args: { rule: { ...RULE, tableNames: ["tmp_*"] } },
  play: async ({ args }) => {
    await screen.findByRole("dialog", { name: "Edit rule" });
    await userEvent.click(within(dialog()).getByRole("button", { name: "Remove table name glob tmp_*" }));
    await userEvent.click(within(dialog()).getByRole("button", { name: "Update rule" }));
    await expect(within(dialog()).getByRole("alert")).toHaveTextContent(
      "A rule needs at least one condition: a namespace or a table name glob.",
    );
    await expect(args.onSubmit).not.toHaveBeenCalled();
  },
};

// The dialog opens on its Close button; Tab reaches every control in order, the outcome is picked
// with the arrow keys, a glob is added with Enter, and Enter on Update rule submits.
export const Keyboard: Story = {
  args: { rule: { ...RULE, tableNames: ["tmp_*"] } },
  play: async ({ args }) => {
    await screen.findByRole("dialog", { name: "Edit rule" });
    await waitFor(() => expect(within(dialog()).getByRole("button", { name: "Close" })).toHaveFocus());
    await userEvent.tab();
    const outcome = within(dialog()).getByRole("combobox", { name: "Outcome" });
    await expect(outcome).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await screen.findByRole("listbox");
    await userEvent.keyboard("{ArrowUp}{Enter}");
    await waitFor(() => expect(outcome).toHaveTextContent("Manage"));
    await expect(outcome).toHaveFocus();
    await userEvent.tab();
    await expect(within(dialog()).getByRole("textbox", { name: "New namespace glob" })).toHaveFocus();
    await userEvent.keyboard("sales{Enter}");
    await userEvent.tab();
    await expect(within(dialog()).getByRole("button", { name: "Add namespace glob" })).toHaveFocus();
    await userEvent.tab();
    await expect(within(dialog()).getByRole("button", { name: "Remove table name glob tmp_*" })).toHaveFocus();
    await userEvent.tab();
    await expect(within(dialog()).getByRole("textbox", { name: "New table name glob" })).toHaveFocus();
    await userEvent.tab();
    await expect(within(dialog()).getByRole("button", { name: "Add table name glob" })).toHaveFocus();
    await userEvent.tab();
    await expect(within(dialog()).getByRole("button", { name: "Cancel" })).toHaveFocus();
    await userEvent.tab();
    await expect(within(dialog()).getByRole("button", { name: "Update rule" })).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await expect(args.onSubmit).toHaveBeenCalledWith({ ...RULE, outcome: "manage", namespaces: ["sales"], tableNames: ["tmp_*"] });
  },
};

export const Escape: Story = {
  play: async ({ args }) => {
    await screen.findByRole("dialog", { name: "Edit rule" });
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(args.onClose).toHaveBeenCalled());
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await screen.findByRole("dialog", { name: "Edit rule" });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
