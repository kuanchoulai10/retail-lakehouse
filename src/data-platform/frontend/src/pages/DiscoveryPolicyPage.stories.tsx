import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, waitFor, within } from "storybook/test";
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

// sales-tables v2: include every table, then exclude the temporary and the staging ones.
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
    await expect(canvas.queryByRole("combobox", { name: "When no rule matches" })).toBeNull();
    const rules = within(canvas.getByRole("table", { name: RULES_TABLE }));
    await expect(rules.getByRole("combobox", { name: "Action of rule 1" })).toHaveTextContent("Include");
    await expect(rules.getByRole("textbox", { name: "Table name pattern of rule 1" })).toHaveValue("*");
    await expect(rules.getByRole("combobox", { name: "Action of rule 2" })).toHaveTextContent("Exclude");
    await expect(rules.getByRole("textbox", { name: "Table name pattern of rule 2" })).toHaveValue("tmp_*");
    const attached = within(canvas.getByRole("region", { name: "Attached to" }));
    await expect(await attached.findByRole("link", { name: "iceberg.sales" })).toBeVisible();
    await expect(await attached.findByText(/^Scanned/)).toBeVisible();
    await expect(canvas.getByRole("button", { name: "Save" })).toBeDisabled();
    const current = canvas.getAllByRole("link", { name: "Discovery policies" }).filter((link) => link.getAttribute("aria-current") === "page");
    await expect(current).toHaveLength(1);
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
    await expect(canvas.queryByDisplayValue("tmp_*")).toBeNull();
  },
};

export const Refused: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("put", "/v1/discovery-policies/:name", "a discovery policy needs at least one rule", 422));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(await canvas.findByRole("textbox", { name: "Description" }), "!");
    await userEvent.click(canvas.getByRole("button", { name: "Save" }));
    await expect(await canvas.findByText("a discovery policy needs at least one rule")).toBeVisible();
  },
};

// A new rule starts as include with no pattern, and Save waits until it has one.
export const AddRule: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("button", { name: "Add rule" }));
    const rules = within(canvas.getByRole("table", { name: RULES_TABLE }));
    await expect(rules.getByRole("combobox", { name: "Action of rule 4" })).toHaveTextContent("Include");
    await expect(canvas.getByRole("button", { name: "Save" })).toBeDisabled();
    await expect(
      canvas.getByText("Every rule needs a table name pattern before the policy can be saved."),
    ).toBeVisible();
  },
};

// The whole edit by keyboard: the description, a new rule whose pattern field takes focus, then back
// up to Save.
export const Keyboard: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const description = await canvas.findByRole("textbox", { name: "Description" });
    description.focus();
    await userEvent.keyboard(" (EU)");
    await userEvent.tab();
    const addRule = canvas.getByRole("button", { name: "Add rule" });
    await expect(addRule).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    const pattern = await canvas.findByRole("textbox", { name: "Table name pattern of rule 4" });
    await waitFor(() => expect(pattern).toHaveFocus());
    await userEvent.keyboard("finance_*");
    await expect(pattern).toHaveValue("finance_*");
    const save = canvas.getByRole("button", { name: "Save" });
    for (let i = 0; i < 30 && document.activeElement !== save; i += 1) await userEvent.tab({ shift: true });
    await expect(save).toHaveFocus();
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
