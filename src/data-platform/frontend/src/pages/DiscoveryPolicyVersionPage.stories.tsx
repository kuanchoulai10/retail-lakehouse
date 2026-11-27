import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { apiError } from "@/stories/apiError";
import { ConsolePage } from "@/stories/ConsolePage";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";

const meta = {
  title: "Pages/Discovery policy version",
  component: ConsolePage,
  args: { route: "/discovery-policies/sales-tables/versions/2" },
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof ConsolePage>;

export default meta;
type Story = StoryObj<typeof meta>;

const RULES_TABLE = "Discovery rules, read top to bottom";

export const Loaded: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("heading", { level: 1, name: "sales-tables v2" })).toBeVisible();
    const facts = within(canvas.getByRole("region", { name: "Policy" }));
    await expect(facts.getByText("Sales tables, without the temporary ones")).toBeVisible();
    await expect(facts.queryByText("When no rule matches")).toBeNull();
    const rules = within(canvas.getByRole("table", { name: RULES_TABLE }));
    await expect(rules.getByText("tmp_*")).toBeVisible();
    await expect(rules.getAllByText("Exclude")).toHaveLength(2);
    await expect(rules.queryByRole("button")).toBeNull();
    const crumbs = within(canvas.getByRole("navigation", { name: "Breadcrumb" }));
    await expect(crumbs.getByRole("link", { name: "sales-tables" })).toBeVisible();
    await expect(canvas.queryByRole("textbox")).toBeNull();
  },
};

// v2 dropped v1's archive rule and added the temporary and staging ones.
export const Changes: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const list = within(await canvas.findByRole("list", { name: "Changes from v1" }));
    const rows = list.getAllByRole("listitem");
    await expect(rows).toHaveLength(3);
    await expect(rows[0]).toHaveTextContent("Rule #2RemovedExclude archive_*");
    await expect(rows[1]).toHaveTextContent("Rule #2AddedExclude tmp_*");
    await expect(rows[2]).toHaveTextContent("Rule #3AddedExclude staging_*");
  },
};

export const FirstVersion: Story = {
  args: { route: "/discovery-policies/sales-tables/versions/1" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("heading", { level: 1, name: "sales-tables v1" })).toBeVisible();
    await expect(canvas.getByText("archive_*")).toBeVisible();
    await expect(canvas.getByText("First version")).toBeVisible();
  },
};

export const NotAVersion: Story = {
  args: { route: "/discovery-policies/sales-tables/versions/latest" },
  play: async ({ canvasElement }) => {
    await expect(
      await within(canvasElement).findByText("Could not load sales-tables vlatest: a version is a whole number."),
    ).toBeVisible();
  },
};

export const Error: Story = {
  args: { route: "/discovery-policies/sales-tables/versions/9" },
  beforeEach({ msw }) {
    msw.use(
      apiError("get", "/v1/discovery-policies/:name/versions/:version", "version 9 of discovery policy sales-tables not found", 404),
    );
  },
  play: async ({ canvasElement }) => {
    await expect(
      await within(canvasElement).findByText(
        "Could not load sales-tables v9: version 9 of discovery policy sales-tables not found",
      ),
    ).toBeVisible();
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByRole("list", { name: "Changes from v1" });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
