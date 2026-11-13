import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import {
  getGetCatalogTableQueryKey,
  getListCatalogTablePropertiesQueryKey,
} from "../../api/generated/tables/tables";
import {
  bodyOf,
  callsTo,
  catalogTableFixture,
  catalogTablePropertiesFixture,
  stubCatalogApi,
  type StubHandler,
} from "../../test/catalogApiStub";
import { jsonResponse } from "../../test/fixtures";
import { PropertiesTab } from "./PropertiesTab";

const TABLE = "/v1/catalogs/iceberg/namespaces/retail/tables/orders";

function stub(extra: Record<string, StubHandler> = {}) {
  return stubCatalogApi({
    [`GET ${TABLE}`]: () => jsonResponse(catalogTableFixture()),
    [`GET ${TABLE}/properties`]: () => jsonResponse(catalogTablePropertiesFixture()),
    [`POST ${TABLE}/properties/reset`]: () => jsonResponse(catalogTablePropertiesFixture()),
    ...extra,
  });
}

function renderTab() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidate = vi.spyOn(client, "invalidateQueries");
  render(
    <QueryClientProvider client={client}>
      <PropertiesTab table={catalogTableFixture()} />
    </QueryClientProvider>,
  );
  return { invalidate };
}

function rowOf(key: string): HTMLElement {
  const row = screen.getByText(key).closest("tr");
  if (row === null) throw new Error(`no row for ${key}`);
  return row;
}

function expectRefetchOfTableAndProperties(invalidate: ReturnType<typeof vi.spyOn>) {
  expect(invalidate).toHaveBeenCalledWith({
    queryKey: getListCatalogTablePropertiesQueryKey("iceberg", "retail", "orders"),
  });
  expect(invalidate).toHaveBeenCalledWith({ queryKey: getGetCatalogTableQueryKey("iceberg", "retail", "orders") });
}

describe("PropertiesTab", { timeout: 15_000 }, () => {
  it("lists every property with its current value, default and where the default comes from", async () => {
    stub();
    renderTab();

    const format = within(await screen.findByText("write.format.default").then(() => rowOf("write.format.default")));
    expect(format.getByText("orc")).toBeInTheDocument();
    expect(format.getByText("parquet")).toBeInTheDocument();
    expect(format.getByText("Iceberg")).toBeInTheDocument();
    expect(format.getByText("Modified")).toBeInTheDocument();

    const retries = within(rowOf("commit.retry.num-retries"));
    expect(retries.getByText("Not set")).toBeInTheDocument();
    expect(retries.queryByText("Modified")).not.toBeInTheDocument();
    expect(retries.queryByRole("button")).not.toBeInTheDocument();

    expect(within(rowOf("owner")).getByText("Custom")).toBeInTheDocument();
    expect(within(rowOf("write.target-file-size-bytes")).getByText("Forced by catalog")).toBeInTheDocument();
    expect(screen.getByText(/Defaults of Iceberg 1\.10\.1/)).toBeInTheDocument();
  });

  it("shows only the modified properties when asked", async () => {
    const user = userEvent.setup();
    stub();
    renderTab();
    await screen.findByText("commit.retry.num-retries");

    await user.click(screen.getByRole("switch", { name: "Show modified only" }));

    expect(screen.queryByText("commit.retry.num-retries")).not.toBeInTheDocument();
    expect(screen.queryByText("format-version")).not.toBeInTheDocument();
    expect(screen.getByText("write.format.default")).toBeInTheDocument();
    expect(screen.getByText("owner")).toBeInTheDocument();
  });

  it("resets one property with the loaded uuid and refetches the table and its properties", async () => {
    const user = userEvent.setup();
    const calls = stub();
    const { invalidate } = renderTab();
    await screen.findByText("write.format.default");

    await user.click(within(rowOf("write.format.default")).getByRole("button", { name: "Reset write.format.default" }));

    await vi.waitFor(() => expect(callsTo(calls, "POST", `${TABLE}/properties/reset`)).toHaveLength(1));
    expect(bodyOf(calls, "POST", `${TABLE}/properties/reset`)).toEqual({
      expected_uuid: "uuid-orders",
      keys: ["write.format.default"],
    });
    await vi.waitFor(() => expectRefetchOfTableAndProperties(invalidate));
  });

  it("deletes a custom property and offers no reset for one that is not resettable", async () => {
    const user = userEvent.setup();
    const calls = stub();
    renderTab();
    await screen.findByText("owner");

    expect(within(rowOf("gc.enabled")).queryByRole("button")).not.toBeInTheDocument();
    expect(within(rowOf("gc.enabled")).getByText("Not resettable")).toBeInTheDocument();
    expect(within(rowOf("write.target-file-size-bytes")).queryByRole("button")).not.toBeInTheDocument();
    await user.click(within(rowOf("owner")).getByRole("button", { name: "Delete owner" }));

    await vi.waitFor(() =>
      expect(bodyOf(calls, "POST", `${TABLE}/properties/reset`)).toEqual({
        expected_uuid: "uuid-orders",
        keys: ["owner"],
      }),
    );
  });

  it("shows a failed reset and still refetches", async () => {
    const user = userEvent.setup();
    stub({
      [`POST ${TABLE}/properties/reset`]: () =>
        jsonResponse({ detail: "format-version cannot be reset: removing it would change the table unsafely" }, 422),
    });
    const { invalidate } = renderTab();
    await screen.findByText("write.format.default");

    await user.click(screen.getByRole("button", { name: "Reset write.format.default" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("format-version cannot be reset");
    await vi.waitFor(() => expectRefetchOfTableAndProperties(invalidate));
  });

  it("resets every modified resettable property after confirming", async () => {
    const user = userEvent.setup();
    const calls = stub();
    renderTab();
    await screen.findByText("write.format.default");

    await user.click(screen.getByRole("button", { name: "Reset all to default" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Reset all to default" });
    expect(dialog).toHaveTextContent("iceberg / retail / orders");
    expect(dialog).toHaveTextContent("resets 1 property to default and deletes 1 custom property");
    expect(within(dialog).getByText("write.format.default")).toBeInTheDocument();
    expect(within(dialog).getByText("owner")).toBeInTheDocument();
    expect(within(dialog).queryByText("gc.enabled")).not.toBeInTheDocument();
    expect(callsTo(calls, "POST", `${TABLE}/properties/reset`)).toHaveLength(0);
    await user.click(within(dialog).getByRole("button", { name: "Reset all" }));

    await vi.waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
    expect(bodyOf(calls, "POST", `${TABLE}/properties/reset`)).toEqual({
      expected_uuid: "uuid-orders",
      keys: ["owner", "write.format.default"],
    });
  });

  it("cancelling reset all sends nothing", async () => {
    const user = userEvent.setup();
    const calls = stub();
    renderTab();
    await screen.findByText("write.format.default");

    await user.click(screen.getByRole("button", { name: "Reset all to default" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Reset all to default" });
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(callsTo(calls, "POST", `${TABLE}/properties/reset`)).toHaveLength(0);
  });

  it("disables reset all when nothing can be reset", async () => {
    stub({
      [`GET ${TABLE}/properties`]: () =>
        jsonResponse(
          catalogTablePropertiesFixture({
            properties: catalogTablePropertiesFixture().properties.filter((p) => !p.modified || !p.resettable),
          }),
        ),
    });
    renderTab();
    await screen.findByText("gc.enabled");

    expect(screen.getByRole("button", { name: "Reset all to default" })).toBeDisabled();
  });

  it("edits properties in the tab and refetches the properties after the save", async () => {
    const user = userEvent.setup();
    const calls = stub({ [`PUT ${TABLE}/properties`]: () => jsonResponse(catalogTableFixture()) });
    const { invalidate } = renderTab();
    await screen.findByText("write.format.default");

    await user.click(screen.getByRole("button", { name: "Edit properties" }));
    const dialog = await screen.findByRole("dialog", { name: "Edit properties" });
    await user.click(within(dialog).getByRole("button", { name: "Remove owner" }));
    await user.click(within(dialog).getByRole("button", { name: "Save" }));

    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(bodyOf(calls, "PUT", `${TABLE}/properties`)).toEqual({
      expected_uuid: "uuid-orders",
      updates: {},
      removals: ["owner"],
    });
    expectRefetchOfTableAndProperties(invalidate);
  });

  it("shows why the properties could not be loaded", async () => {
    stub({ [`GET ${TABLE}/properties`]: () => jsonResponse({ detail: "polaris unreachable" }, 502) });
    renderTab();

    expect(await screen.findByText(/Could not load properties: polaris unreachable/)).toBeInTheDocument();
  });
});
