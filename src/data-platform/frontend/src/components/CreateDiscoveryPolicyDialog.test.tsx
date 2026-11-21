import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useParams } from "react-router";
import { describe, expect, it, vi } from "vitest";
import type { TableDiscoveryPolicyApiResponse } from "../api/generated/model";
import { bodyOf, callsTo, stubCatalogApi, type StubHandler } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { CreateDiscoveryPolicyDialog } from "./CreateDiscoveryPolicyDialog";

const CREATED: TableDiscoveryPolicyApiResponse = {
  id: "dp-01m7s6c3tqee0rhg00xry2zqqw",
  name: "orders-only",
  is_default: false,
  version: 1,
  description: "",
  no_match_outcome: "unmanage",
  rules: [],
  created_at: "2026-11-21T09:00:00Z",
  updated_at: "2026-11-21T09:00:00Z",
};

function PolicyProbe() {
  const { name = "" } = useParams();
  return <p>Policy page {name}</p>;
}

function renderDialog(create: StubHandler = () => jsonResponse(CREATED, 201)) {
  const calls = stubCatalogApi({
    "POST /v1/discovery-policies": create,
    "GET /v1/discovery-policies": () => jsonResponse({ policies: [] }),
  });
  const onClose = vi.fn();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/discovery-policies"]}>
        <Routes>
          <Route path="/discovery-policies" element={<CreateDiscoveryPolicyDialog onClose={onClose} />} />
          <Route path="/discovery-policies/:name" element={<PolicyProbe />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { calls, onClose, client };
}

function dialog(): HTMLElement {
  return screen.getByRole("dialog", { name: "New discovery policy" });
}

describe("CreateDiscoveryPolicyDialog", { timeout: 15_000 }, () => {
  it("asks for a name, a description and what happens when no rule matches, preset to Do not manage", () => {
    renderDialog();
    expect(within(dialog()).getByRole("textbox", { name: "Name" })).toHaveValue("");
    expect(within(dialog()).getByRole("textbox", { name: "Description" })).toHaveValue("");
    expect(within(dialog()).getByRole("combobox", { name: "When no rule matches" })).toHaveTextContent(
      "Do not manage",
    );
  });

  it("creates a policy with no rules and goes to its page", async () => {
    const user = userEvent.setup();
    const { calls, onClose } = renderDialog();
    await user.type(within(dialog()).getByRole("textbox", { name: "Name" }), " orders-only ");
    await user.type(within(dialog()).getByRole("textbox", { name: "Description" }), "Orders tables");
    await user.click(within(dialog()).getByRole("button", { name: "Create policy" }));

    expect(await screen.findByText("Policy page orders-only")).toBeInTheDocument();
    expect(bodyOf(calls, "POST", "/v1/discovery-policies")).toEqual({
      name: "orders-only",
      description: "Orders tables",
      no_match_outcome: "unmanage",
      rules: [],
    });
    expect(onClose).toHaveBeenCalled();
  });

  it("sends Manage when it is picked for tables no rule matches", async () => {
    const user = userEvent.setup();
    const { calls } = renderDialog();
    await user.type(within(dialog()).getByRole("textbox", { name: "Name" }), "everything");
    await user.click(within(dialog()).getByRole("combobox", { name: "When no rule matches" }));
    await user.click(await screen.findByRole("option", { name: "Manage" }));
    await user.click(within(dialog()).getByRole("button", { name: "Create policy" }));

    await waitFor(() =>
      expect(bodyOf(calls, "POST", "/v1/discovery-policies")).toMatchObject({ no_match_outcome: "manage" }),
    );
  });

  it("refetches the policy list after a create", async () => {
    const user = userEvent.setup();
    const { client } = renderDialog();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    await user.type(within(dialog()).getByRole("textbox", { name: "Name" }), "orders-only");
    await user.click(within(dialog()).getByRole("button", { name: "Create policy" }));

    await screen.findByText("Policy page orders-only");
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["/v1/discovery-policies"], exact: true });
  });

  it("refuses a name the API would refuse without asking it", async () => {
    const user = userEvent.setup();
    const { calls } = renderDialog();
    await user.type(within(dialog()).getByRole("textbox", { name: "Name" }), "has space");
    await user.click(within(dialog()).getByRole("button", { name: "Create policy" }));

    expect(
      await within(dialog()).findByText("A name uses letters, digits, - and _ only, at most 64 characters."),
    ).toBeInTheDocument();
    expect(callsTo(calls, "POST", "/v1/discovery-policies")).toEqual([]);
  });

  it.each([
    [409, "a discovery policy named orders-only already exists"],
    [422, "a policy name is not shaped like a prefixed id"],
  ])("shows the API's detail for a %i and stays open", async (status, detail) => {
    const user = userEvent.setup();
    const { onClose } = renderDialog(() => jsonResponse({ detail }, status));
    await user.type(within(dialog()).getByRole("textbox", { name: "Name" }), "orders-only");
    await user.click(within(dialog()).getByRole("button", { name: "Create policy" }));

    expect(await within(dialog()).findByText(detail)).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.queryByText(/Policy page/)).not.toBeInTheDocument();
  });
});
