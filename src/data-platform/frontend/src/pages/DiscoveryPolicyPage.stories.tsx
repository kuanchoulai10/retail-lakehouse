import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, screen, userEvent, waitFor, within } from "storybook/test";
import { apiError } from "@/stories/apiError";
import { ConsolePage } from "@/stories/ConsolePage";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";

const meta = {
  title: "Pages/Discovery policy",
  component: ConsolePage,
  args: { route: "/discovery-policies/sales-tables" },
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof ConsolePage>;

export default meta;
type Story = StoryObj<typeof meta>;

const RULES_TABLE = "Discovery rules, read top to bottom";

// sales-tables v2: manage the sales namespaces' orders and returns, keep temporary tables out.
export const Loaded: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("heading", { level: 1, name: "sales-tables" })).toBeVisible();
    await expect(canvas.getByText(/^Version 2, saved/)).toBeVisible();
    const versions = within(canvas.getByRole("navigation", { name: "Versions" }));
    await expect(versions.getAllByRole("link").map((link) => link.textContent)).toEqual(["v2", "v1"]);
    await expect(canvas.getByRole("textbox", { name: "Description" })).toHaveValue(
      "Sales tables, without the temporary ones",
    );
    await expect(canvas.getByRole("combobox", { name: "When no rule matches" })).toHaveTextContent("Do not manage");
    const rules = within(canvas.getByRole("table", { name: RULES_TABLE }));
    await expect(rules.getByText("orders*")).toBeVisible();
    await expect(rules.getByText("tmp_*")).toBeVisible();
    // Attached to namespace iceberg.sales, so rule 1's namespace globs only tell its child namespaces apart.
    await expect(
      await rules.findByText(
        "Attached to namespace iceberg.sales: a namespace glob only tells its child namespaces apart.",
      ),
    ).toBeVisible();
    const attached = within(canvas.getByRole("region", { name: "Attached to" }));
    await expect(attached.getByRole("link", { name: "iceberg.sales" })).toBeVisible();
    await expect(await attached.findByText(/^Scanned/)).toBeVisible();
    await expect(canvas.getByRole("button", { name: "Save" })).toBeDisabled();
    const current = canvas.getAllByRole("link", { name: "Discovery policies" }).filter((link) => link.getAttribute("aria-current") === "page");
    await expect(current).toHaveLength(1);
  },
};

// The platform default reads only: its fixed description, no rules and nothing to save.
export const Default: Story = {
  args: { route: "/discovery-policies/default" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("heading", { level: 1, name: "default" })).toBeVisible();
    await expect(
      canvas.getByText(
        "Manages nothing. Attach another discovery policy to a catalog, namespace or table to manage its tables.",
      ),
    ).toBeVisible();
    await expect(canvas.getByText("No rules.")).toBeVisible();
    await expect(canvas.queryByRole("button", { name: "Save" })).toBeNull();
    await expect(canvas.queryByRole("textbox")).toBeNull();
  },
};

export const Saved: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("button", { name: "Delete rule 2" }));
    await expect(canvas.queryByRole("dialog")).toBeNull();
    await userEvent.click(canvas.getByRole("button", { name: "Save" }));
    await expect(await canvas.findByText("Saved. Discovering tables…")).toBeVisible();
  },
};

export const Conflict: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("put", "/v1/discovery-policies/:name", "policy sales-tables is at version 3, not 2", 409));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("button", { name: "Delete rule 2" }));
    await userEvent.click(canvas.getByRole("button", { name: "Save" }));
    await expect(
      await canvas.findByText("Someone else changed this policy. Reload to see their version."),
    ).toBeVisible();
    await expect(canvas.getByRole("button", { name: "Reload" })).toBeVisible();
    await expect(canvas.queryByText("tmp_*")).toBeNull();
  },
};

export const Refused: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("put", "/v1/discovery-policies/:name", "unknown discovery rule id dr-01m7s6c3tqee0rhg00xz1dk9cz", 422));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(await canvas.findByRole("textbox", { name: "Description" }), "!");
    await userEvent.click(canvas.getByRole("button", { name: "Save" }));
    await expect(await canvas.findByText("unknown discovery rule id dr-01m7s6c3tqee0rhg00xz1dk9cz")).toBeVisible();
  },
};

// The whole edit by keyboard: the description, a new rule through the editor, focus back on Add
// rule when it closes, then back up to Save.
export const Keyboard: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const description = await canvas.findByRole("textbox", { name: "Description" });
    description.focus();
    await userEvent.keyboard(" (EU)");
    await userEvent.tab();
    await expect(canvas.getByRole("combobox", { name: "When no rule matches" })).toHaveFocus();
    await userEvent.tab();
    const addRule = canvas.getByRole("button", { name: "Add rule" });
    await expect(addRule).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    const dialog = await screen.findByRole("dialog", { name: "Add rule" });
    await waitFor(() => expect(within(dialog).getByRole("button", { name: "Close" })).toHaveFocus());
    await userEvent.tab();
    await expect(within(dialog).getByRole("combobox", { name: "Outcome" })).toHaveFocus();
    await userEvent.tab();
    await userEvent.keyboard("finance{Enter}");
    for (let i = 0; i < 5; i += 1) await userEvent.tab();
    await expect(within(dialog).getByRole("button", { name: "Add rule" })).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(addRule).toHaveFocus());
    await expect(within(canvas.getByRole("table", { name: RULES_TABLE })).getByText("finance")).toBeVisible();
    await userEvent.tab({ shift: true });
    await userEvent.tab({ shift: true });
    await userEvent.tab({ shift: true });
    await expect(canvas.getByRole("button", { name: "Save" })).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await expect(await canvas.findByText("Saved. Discovering tables…")).toBeVisible();
  },
};

export const Error: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("get", "/v1/discovery-policies/:name", "database unavailable"));
  },
  play: async ({ canvasElement }) => {
    await expect(
      await within(canvasElement).findByText("Could not load discovery policy sales-tables: database unavailable"),
    ).toBeVisible();
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByRole("table", { name: RULES_TABLE });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
