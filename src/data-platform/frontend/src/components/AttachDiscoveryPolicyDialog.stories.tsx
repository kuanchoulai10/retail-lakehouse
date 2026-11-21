import type { Meta, StoryObj } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, fn, screen, userEvent, waitFor, within } from "storybook/test";
import { apiError } from "@/stories/apiError";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";
import { AttachDiscoveryPolicyDialog } from "./AttachDiscoveryPolicyDialog";

const meta = {
  title: "Components/Attach discovery policy dialog",
  component: AttachDiscoveryPolicyDialog,
  args: { policyName: "sales-tables", onClose: fn() },
  decorators: [
    (Story) => (
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <Story />
      </QueryClientProvider>
    ),
  ],
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof AttachDiscoveryPolicyDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

function dialog(): HTMLElement {
  return screen.getByRole("dialog", { name: "Attach sales-tables" });
}

async function choose(field: string, option: string) {
  await userEvent.click(await within(dialog()).findByRole("combobox", { name: field }));
  await userEvent.click(await screen.findByRole("option", { name: option }));
}

export const Catalog: Story = {
  play: async ({ args }) => {
    await screen.findByRole("dialog", { name: "Attach sales-tables" });
    await expect(within(dialog()).queryByRole("textbox", { name: "Namespace" })).toBeNull();
    await choose("Catalog", "iceberg");
    await userEvent.click(within(dialog()).getByRole("button", { name: "Attach" }));
    await waitFor(() => expect(args.onClose).toHaveBeenCalled());
  },
};

export const Table: Story = {
  play: async () => {
    await screen.findByRole("dialog", { name: "Attach sales-tables" });
    await choose("Type", "Table");
    await expect(within(dialog()).getByRole("textbox", { name: "Namespace" })).toBeVisible();
    await expect(within(dialog()).getByRole("textbox", { name: "Table" })).toBeVisible();
  },
};

// The dialog opens on its Close button; Tab reaches each field in turn, the selects open with
// Enter and move with the arrow keys, and Enter on Attach sends it.
export const Keyboard: Story = {
  play: async ({ args }) => {
    await screen.findByRole("dialog", { name: "Attach sales-tables" });
    await within(dialog()).findByRole("combobox", { name: "Catalog" });
    await waitFor(() => expect(within(dialog()).getByRole("button", { name: "Close" })).toHaveFocus());
    await userEvent.tab();
    const type = within(dialog()).getByRole("combobox", { name: "Type" });
    await expect(type).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await screen.findByRole("listbox");
    await userEvent.keyboard("{ArrowDown}{Enter}");
    await waitFor(() => expect(type).toHaveTextContent("Namespace"));
    await expect(type).toHaveFocus();
    await userEvent.tab();
    const catalog = within(dialog()).getByRole("combobox", { name: "Catalog" });
    await expect(catalog).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await screen.findByRole("listbox");
    await userEvent.keyboard("{ArrowDown}{Enter}");
    await waitFor(() => expect(catalog).toHaveTextContent("iceberg"));
    await userEvent.tab();
    await expect(within(dialog()).getByRole("textbox", { name: "Namespace" })).toHaveFocus();
    await userEvent.keyboard("sales.eu");
    await userEvent.tab();
    await expect(within(dialog()).getByRole("button", { name: "Cancel" })).toHaveFocus();
    await userEvent.tab();
    await expect(within(dialog()).getByRole("button", { name: "Attach" })).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await waitFor(() => expect(args.onClose).toHaveBeenCalled());
  },
};

export const EscapeCloses: Story = {
  play: async ({ args }) => {
    await screen.findByRole("dialog", { name: "Attach sales-tables" });
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(args.onClose).toHaveBeenCalled());
  },
};

export const NotFound: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("put", "/v1/discovery-policies/:name/attachments", "namespace iceberg.sales.eu not found", 404));
  },
  play: async ({ args }) => {
    await screen.findByRole("dialog", { name: "Attach sales-tables" });
    await choose("Type", "Namespace");
    await choose("Catalog", "iceberg");
    await userEvent.type(within(dialog()).getByRole("textbox", { name: "Namespace" }), "sales.eu");
    await userEvent.click(within(dialog()).getByRole("button", { name: "Attach" }));
    await expect(await within(dialog()).findByText("namespace iceberg.sales.eu not found")).toBeVisible();
    await expect(args.onClose).not.toHaveBeenCalled();
  },
};

export const CannotAccess: Story = {
  beforeEach({ msw }) {
    msw.use(
      apiError(
        "put",
        "/v1/discovery-policies/:name/attachments",
        "the platform's catalog credential cannot read catalog analytics",
        403,
      ),
    );
  },
  play: async ({ args }) => {
    await screen.findByRole("dialog", { name: "Attach sales-tables" });
    await choose("Catalog", "analytics");
    await userEvent.click(within(dialog()).getByRole("button", { name: "Attach" }));
    await expect(
      await within(dialog()).findByText("the platform's catalog credential cannot read catalog analytics"),
    ).toBeVisible();
    await expect(args.onClose).not.toHaveBeenCalled();
  },
};

export const NothingChosen: Story = {
  play: async ({ args }) => {
    await screen.findByRole("dialog", { name: "Attach sales-tables" });
    await within(dialog()).findByRole("combobox", { name: "Catalog" });
    await userEvent.click(within(dialog()).getByRole("button", { name: "Attach" }));
    await expect(await within(dialog()).findByText("Choose a catalog.")).toBeVisible();
    await expect(args.onClose).not.toHaveBeenCalled();
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await screen.findByRole("dialog", { name: "Attach sales-tables" });
    await choose("Type", "Table");
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
