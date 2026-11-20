import type { Meta, StoryObj } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { expect, fn, screen, userEvent, waitFor, within } from "storybook/test";
import { apiError } from "@/stories/apiError";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { PHONE } from "@/stories/phone";
import { DEFAULT_POLICY_CONTENT, POLICIES } from "@/stories/storyData";
import { PolicyEditor } from "./PolicyEditor";

const DEFAULT = POLICIES[0]!;
const WITHOUT_COMMITS = POLICIES[1]!;
const ONLY_REWRITE_DATA_FILES = POLICIES[2]!;

const meta = {
  title: "Components/Policy editor",
  component: PolicyEditor,
  args: { policy: DEFAULT, content: DEFAULT, onClose: fn() },
  decorators: [
    (Story) => (
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter>
          <Story />
        </MemoryRouter>
      </QueryClientProvider>
    ),
  ],
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof PolicyEditor>;

export default meta;
type Story = StoryObj<typeof meta>;

function section(dialog: HTMLElement, name: string) {
  return within(within(dialog).getByRole("group", { name }));
}

export const DefaultPolicy: Story = {
  play: async ({ args }) => {
    const dialog = await screen.findByRole("dialog", { name: "Edit policy" });
    await expect(within(dialog).getByRole("textbox", { name: "Check every (seconds)" })).toHaveValue("3600");
    await expect(within(dialog).getByRole("textbox", { name: "Debounce (seconds)" })).toHaveValue("300");
    await expect(section(dialog, "Expire snapshots").getByRole("textbox", { name: "Min snapshots to keep" })).toHaveValue("10");
    await expect(within(dialog).getByRole("link", { name: "platform settings" })).toBeVisible();
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(args.onClose).toHaveBeenCalled());
  },
};

export const WithoutCatalogCommits: Story = {
  args: { policy: WITHOUT_COMMITS, content: WITHOUT_COMMITS },
  play: async () => {
    const dialog = await screen.findByRole("dialog", { name: "Edit policy" });
    await expect(within(dialog).getByRole("switch", { name: "Check after catalog commits" })).not.toBeChecked();
    await expect(within(dialog).queryByRole("textbox", { name: "Debounce (seconds)" })).toBeNull();
    await expect(section(dialog, "Rewrite data files").getByRole("combobox", { name: "Per" })).toHaveTextContent("Whole table");
    await expect(section(dialog, "Rewrite data files").getByRole("combobox", { name: "Strategy" })).toHaveTextContent("Sort");
  },
};

export const OnlyRewriteDataFiles: Story = {
  args: { policy: ONLY_REWRITE_DATA_FILES, content: ONLY_REWRITE_DATA_FILES },
  play: async () => {
    const dialog = await screen.findByRole("dialog", { name: "Edit policy" });
    for (const name of ["Rewrite manifests", "Expire snapshots", "Remove orphan files"]) {
      await expect(section(dialog, name).getByRole("switch", { name: "In this policy" })).not.toBeChecked();
      await expect(section(dialog, name).getByText("Not in this policy: this operation does not run on a schedule.")).toBeVisible();
    }
    await expect(section(dialog, "Rewrite data files").getByRole("switch", { name: "In this policy" })).toBeChecked();
  },
};

export const New: Story = {
  args: { policy: undefined, content: { ...DEFAULT_POLICY_CONTENT, description: "" } },
  play: async () => {
    const dialog = await screen.findByRole("dialog", { name: "New policy" });
    await expect(within(dialog).getByRole("textbox", { name: "Name" })).toHaveValue("");
  },
};

export const Invalid: Story = {
  play: async ({ args }) => {
    const dialog = await screen.findByRole("dialog", { name: "Edit policy" });
    const every = within(dialog).getByRole("textbox", { name: "Check every (seconds)" });
    await userEvent.clear(every);
    await userEvent.type(every, "30");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await expect(within(dialog).getByRole("alert")).toHaveTextContent("Check every must be 60 to 604800 seconds.");
    await expect(args.onClose).not.toHaveBeenCalled();
  },
};

export const Refused: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("put", "/v1/maintenance-policies/default", "remove_orphan_files.target.older_than_seconds must be at least 86400", 422));
  },
  play: async ({ args }) => {
    const dialog = await screen.findByRole("dialog", { name: "Edit policy" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await expect(
      await within(dialog).findByText("remove_orphan_files.target.older_than_seconds must be at least 86400"),
    ).toBeVisible();
    await expect(args.onClose).not.toHaveBeenCalled();
  },
};

// Tab reaches Check every from the description, Space flips the switches, and the fields they
// govern disappear and come back with their values.
export const Keyboard: Story = {
  play: async ({ args }) => {
    const dialog = await screen.findByRole("dialog", { name: "Edit policy" });
    within(dialog).getByRole("textbox", { name: "Description" }).focus();
    await userEvent.tab();
    await expect(within(dialog).getByRole("textbox", { name: "Check every (seconds)" })).toHaveFocus();
    await userEvent.tab();
    await expect(within(dialog).getByRole("switch", { name: "Check after catalog commits" })).toHaveFocus();
    await userEvent.keyboard(" ");
    await expect(within(dialog).queryByRole("textbox", { name: "Debounce (seconds)" })).toBeNull();
    await userEvent.keyboard(" ");
    await expect(within(dialog).getByRole("textbox", { name: "Debounce (seconds)" })).toHaveValue("300");

    const included = section(dialog, "Remove orphan files").getByRole("switch", { name: "In this policy" });
    included.focus();
    await userEvent.keyboard(" ");
    await expect(section(dialog, "Remove orphan files").queryByRole("textbox", { name: "Older than (seconds)" })).toBeNull();
    await userEvent.keyboard(" ");
    await expect(section(dialog, "Remove orphan files").getByRole("textbox", { name: "Older than (seconds)" })).toHaveValue(
      "259200",
    );

    await userEvent.keyboard("{Escape}");
    await expect(args.onClose).toHaveBeenCalled();
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await screen.findByRole("dialog", { name: "Edit policy" });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
