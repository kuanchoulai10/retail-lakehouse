import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, screen, userEvent, within } from "storybook/test";
import type { DiscoveryRuleDraft } from "@/lib/discoveryRuleDraft";
import { DiscoveryRuleEditor } from "./DiscoveryRuleEditor";

const RULE_ID = "dr-01m7s6c3tqee0rhg00xz1dk9cs";

const RULE: DiscoveryRuleDraft = {
  key: RULE_ID,
  id: RULE_ID,
  priority: 50,
  action: "exclude",
  enabled: true,
  catalogs: ["*"],
  namespaces: ["prod.*"],
  tables: ["tmp_*", "staging_*"],
};

const meta = {
  title: "Components/Discovery rule editor",
  component: DiscoveryRuleEditor,
  args: { title: "Edit rule", submitLabel: "Update rule", rule: RULE, onSubmit: fn(), onClose: fn() },
} satisfies Meta<typeof DiscoveryRuleEditor>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Edit: Story = {
  play: async ({ args }) => {
    const dialog = await screen.findByRole("dialog", { name: "Edit rule" });
    await userEvent.type(within(dialog).getByRole("textbox", { name: "New tables glob" }), "scratch_*{Enter}");
    await userEvent.click(within(dialog).getByRole("button", { name: "Update rule" }));
    await expect(args.onSubmit).toHaveBeenCalledWith({ ...RULE, tables: ["tmp_*", "staging_*", "scratch_*"] });
  },
};

export const Add: Story = {
  args: {
    title: "Add rule",
    submitLabel: "Add rule",
    rule: { ...RULE, key: "new-1", id: null, action: "include", catalogs: ["*"], namespaces: ["*"], tables: ["*"] },
  },
};

export const Invalid: Story = {
  play: async ({ args }) => {
    const dialog = await screen.findByRole("dialog", { name: "Edit rule" });
    await userEvent.clear(within(dialog).getByRole("spinbutton", { name: "Priority" }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Update rule" }));
    await expect(within(dialog).getByRole("alert")).toHaveTextContent("Priority must be a whole number.");
    await expect(args.onSubmit).not.toHaveBeenCalled();
  },
};

export const Escape: Story = {
  play: async ({ args }) => {
    await screen.findByRole("dialog", { name: "Edit rule" });
    await userEvent.keyboard("{Escape}");
    await expect(args.onClose).toHaveBeenCalled();
  },
};
