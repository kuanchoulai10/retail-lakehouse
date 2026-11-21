import type { Meta, StoryObj } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes, useParams } from "react-router";
import { expect, fn, screen, userEvent, waitFor, within } from "storybook/test";
import { apiError } from "@/stories/apiError";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";
import { CreateDiscoveryPolicyDialog } from "./CreateDiscoveryPolicyDialog";

function PolicyPageProbe() {
  const { name = "" } = useParams();
  return <p>Policy page {name}</p>;
}

const meta = {
  title: "Components/Create discovery policy dialog",
  component: CreateDiscoveryPolicyDialog,
  args: { onClose: fn() },
  decorators: [
    (Story) => (
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={["/discovery-policies"]}>
          <Routes>
            <Route path="/discovery-policies" element={<Story />} />
            <Route path="/discovery-policies/:name" element={<PolicyPageProbe />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    ),
  ],
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof CreateDiscoveryPolicyDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

function dialog(): HTMLElement {
  return screen.getByRole("dialog", { name: "New discovery policy" });
}

export const Empty: Story = {
  play: async () => {
    await screen.findByRole("dialog", { name: "New discovery policy" });
    await expect(within(dialog()).getByRole("textbox", { name: "Name" })).toHaveValue("");
    await expect(within(dialog()).getByRole("textbox", { name: "Description" })).toHaveValue("");
    await expect(within(dialog()).getByRole("combobox", { name: "When no rule matches" })).toHaveTextContent(
      "Do not manage",
    );
  },
};

// The dialog opens on its Close button; every field is reached with Tab from there, the outcome
// is picked with the arrow keys, and Enter on Create policy creates.
export const Keyboard: Story = {
  play: async () => {
    await screen.findByRole("dialog", { name: "New discovery policy" });
    await waitFor(() => expect(within(dialog()).getByRole("button", { name: "Close" })).toHaveFocus());
    await userEvent.tab();
    const name = within(dialog()).getByRole("textbox", { name: "Name" });
    await expect(name).toHaveFocus();
    await userEvent.keyboard("sales-all");
    await userEvent.tab();
    await expect(within(dialog()).getByRole("textbox", { name: "Description" })).toHaveFocus();
    await userEvent.tab();
    const outcome = within(dialog()).getByRole("combobox", { name: "When no rule matches" });
    await expect(outcome).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await screen.findByRole("listbox");
    await userEvent.keyboard("{ArrowUp}{Enter}");
    await waitFor(() => expect(outcome).toHaveTextContent("Manage"));
    await expect(outcome).not.toHaveTextContent("Do not manage");
    await expect(outcome).toHaveFocus();
    await userEvent.tab();
    await expect(within(dialog()).getByRole("button", { name: "Cancel" })).toHaveFocus();
    await userEvent.tab();
    await expect(within(dialog()).getByRole("button", { name: "Create policy" })).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await expect(await screen.findByText("Policy page sales-all")).toBeVisible();
  },
};

export const EscapeCloses: Story = {
  play: async ({ args }) => {
    await screen.findByRole("dialog", { name: "New discovery policy" });
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(args.onClose).toHaveBeenCalled());
  },
};

export const Created: Story = {
  play: async ({ args }) => {
    await screen.findByRole("dialog", { name: "New discovery policy" });
    await userEvent.type(within(dialog()).getByRole("textbox", { name: "Name" }), "orders-only");
    await userEvent.click(within(dialog()).getByRole("button", { name: "Create policy" }));
    await expect(await screen.findByText("Policy page orders-only")).toBeVisible();
    await expect(args.onClose).toHaveBeenCalled();
  },
};

export const NameTaken: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("post", "/v1/discovery-policies", "a discovery policy named sales-tables already exists", 409));
  },
  play: async () => {
    await screen.findByRole("dialog", { name: "New discovery policy" });
    await userEvent.type(within(dialog()).getByRole("textbox", { name: "Name" }), "sales-tables");
    await userEvent.click(within(dialog()).getByRole("button", { name: "Create policy" }));
    await expect(
      await within(dialog()).findByText("a discovery policy named sales-tables already exists"),
    ).toBeVisible();
  },
};

export const Refused: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("post", "/v1/discovery-policies", "a policy name is not shaped like a prefixed id", 422));
  },
  play: async () => {
    await screen.findByRole("dialog", { name: "New discovery policy" });
    await userEvent.type(within(dialog()).getByRole("textbox", { name: "Name" }), "dp-01m7s6c3tqee0rhg00xry2zqqv");
    await userEvent.click(within(dialog()).getByRole("button", { name: "Create policy" }));
    await expect(await within(dialog()).findByText("a policy name is not shaped like a prefixed id")).toBeVisible();
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await screen.findByRole("dialog", { name: "New discovery policy" });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
