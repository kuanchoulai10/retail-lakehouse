import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { beforeEach, describe, expect, it } from "vitest";
import type {
  CatalogTablePartitionSpecComparisonApiResponse,
  CatalogTablePartitionSpecVersionApiResponse,
  CatalogTableSchemaComparisonApiResponse,
  CatalogTableSchemaVersionApiResponse,
  PartitionFieldComparisonApiResponse,
  SchemaChangeCountsApiResponse,
  SchemaFieldComparisonApiResponse,
} from "../../api/generated/model";
import { catalogTableFixture, stubCatalogApi, type StubbedCall, type StubHandler } from "../../test/catalogApiStub";
import { jsonResponse } from "../../test/fixtures";
import { SchemaTab } from "./SchemaTab";

const TABLE = "/v1/catalogs/iceberg/namespaces/retail/tables/orders";
const NONE: SchemaChangeCountsApiResponse = {
  added: 0,
  removed: 0,
  renamed: 0,
  type_changed: 0,
  nullability_changed: 0,
  doc_changed: 0,
};

function schemaVersion(
  id: number,
  changes: SchemaChangeCountsApiResponse | null,
  current = false,
): CatalogTableSchemaVersionApiResponse {
  return {
    schema_id: id,
    previous_schema_id: id === 0 ? null : id - 1,
    current,
    column_count: 6,
    changes,
  };
}

function schemaField(
  id: number,
  path: string[],
  overrides: Partial<SchemaFieldComparisonApiResponse> = {},
): SchemaFieldComparisonApiResponse {
  return {
    field_id: id,
    depth: path.length - 1,
    path,
    previous_path: path,
    type: "long",
    previous_type: "long",
    required: false,
    previous_required: false,
    doc: null,
    previous_doc: null,
    changes: [],
    ...overrides,
  };
}

function added(id: number, path: string[], type = "string"): SchemaFieldComparisonApiResponse {
  return schemaField(id, path, { previous_path: null, type, previous_type: null, previous_required: null, changes: ["added"] });
}

const V1_AGAINST_V0: CatalogTableSchemaComparisonApiResponse = {
  schema_id: 1,
  base_schema_id: 0,
  fields: [
    schemaField(1, ["order_id"], { required: true, previous_required: true, doc: "Order key", previous_doc: "Key", changes: ["doc_changed"] }),
    schemaField(2, ["customer_id"], { required: true, previous_required: true }),
    added(3, ["coupon_code"]),
    added(4, ["address"], "struct"),
    { ...added(5, ["address", "city"]), depth: 1 },
    { ...added(6, ["address", "zip"]), depth: 1 },
    added(7, ["channel"]),
  ],
};

const V0_AGAINST_NOTHING: CatalogTableSchemaComparisonApiResponse = {
  schema_id: 0,
  base_schema_id: null,
  fields: [schemaField(1, ["order_id"], { required: true, previous_required: true }), schemaField(2, ["customer_id"])],
};

const V0_AGAINST_V1: CatalogTableSchemaComparisonApiResponse = {
  schema_id: 0,
  base_schema_id: 1,
  fields: [schemaField(1, ["order_id"]), schemaField(3, ["coupon_code"], { path: null, type: null, required: null, previous_type: "string", changes: ["removed"] })],
};

const SPEC_VERSIONS = {
  default_spec_id: 1,
  versions: [
    { spec_id: 1, previous_spec_id: 0, default: true, field_count: 2, changes: { added: 0, removed: 0, renamed: 0, transform_changed: 1 } },
    { spec_id: 0, previous_spec_id: null, default: false, field_count: 1, changes: null },
  ] satisfies CatalogTablePartitionSpecVersionApiResponse[],
};

function partitionField(overrides: Partial<PartitionFieldComparisonApiResponse>): PartitionFieldComparisonApiResponse {
  return {
    field_id: 1000,
    previous_field_id: 1000,
    name: "order_ts_day",
    previous_name: "order_ts_day",
    transform: "day",
    previous_transform: "day",
    expression: "day(order_ts)",
    previous_expression: "day(order_ts)",
    source_path: ["order_ts"],
    previous_source_path: ["order_ts"],
    changes: [],
    ...overrides,
  };
}

const SPEC_1_AGAINST_0: CatalogTablePartitionSpecComparisonApiResponse = {
  spec_id: 1,
  base_spec_id: 0,
  fields: [
    partitionField({
      field_id: 1001,
      previous_field_id: 1000,
      name: "order_ts_hour",
      transform: "hour",
      expression: "hour(order_ts)",
      changes: ["transform_changed"],
    }),
    partitionField({ field_id: 1002, previous_field_id: 1002, name: "region", previous_name: "region", transform: "identity", previous_transform: "identity", expression: "identity(region)", previous_expression: "identity(region)" }),
  ],
};

const SPEC_0_AGAINST_NOTHING: CatalogTablePartitionSpecComparisonApiResponse = {
  spec_id: 0,
  base_spec_id: null,
  fields: [partitionField({})],
};

const SCHEMA_VERSIONS = {
  current_schema_id: 1,
  versions: [
    schemaVersion(1, { ...NONE, added: 5, doc_changed: 1 }, true),
    schemaVersion(0, null),
  ],
};

function stubSchemaTab(extra: Record<string, StubHandler> = {}): StubbedCall[] {
  return stubCatalogApi({
    [`GET ${TABLE}/schema-versions`]: () => jsonResponse(SCHEMA_VERSIONS),
    [`GET ${TABLE}/schema-versions/1/comparison`]: () => jsonResponse(V1_AGAINST_V0),
    [`GET ${TABLE}/schema-versions/0/comparison`]: () => jsonResponse(V0_AGAINST_NOTHING),
    [`GET ${TABLE}/schema-versions/0/comparison?base=1`]: () => jsonResponse(V0_AGAINST_V1),
    [`GET ${TABLE}/partition-spec-versions`]: () => jsonResponse(SPEC_VERSIONS),
    [`GET ${TABLE}/partition-spec-versions/1/comparison`]: () => jsonResponse(SPEC_1_AGAINST_0),
    [`GET ${TABLE}/partition-spec-versions/0/comparison`]: () => jsonResponse(SPEC_0_AGAINST_NOTHING),
    ...extra,
  });
}

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.search}</output>;
}

function renderTab(search = "", table = catalogTableFixture({ schema: { ...catalogTableFixture().schema, schema_id: 1 } })) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/tables/orders/schema${search}`]}>
        <SchemaTab table={table} />
        <LocationProbe />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function paths(calls: StubbedCall[]): string[] {
  return calls.map((call) => call.path);
}

function versionButton(region: HTMLElement, version: string): HTMLElement {
  return within(region).getByRole("button", { name: new RegExp(`^${version}(?!\\d)`) });
}


describe("SchemaTab", () => {
  let calls: StubbedCall[];

  beforeEach(() => {
    calls = stubSchemaTab();
  });

  it("opens on the current version and asks for its comparison with the previous one", async () => {
    renderTab();
    const schema = screen.getByRole("region", { name: "Schema" });
    const newest = await within(schema).findByRole("button", { name: /^v1(?!\d)/ });
    expect(newest).toHaveTextContent("Current");
    expect(newest).toHaveTextContent("+5 added · 1 doc changed");
    expect(newest).toHaveAttribute("aria-current", "true");
    expect(versionButton(schema, "v0")).toHaveTextContent("First version");
    expect(await within(schema).findByRole("list", { name: "Changes in schema v1" })).toBeInTheDocument();
    expect(paths(calls)).toContain(`${TABLE}/schema-versions/1/comparison`);
    expect(paths(calls).filter((path) => path.includes("base="))).toEqual([]);
  });

  it("puts a chosen version in the url and asks for its comparison", async () => {
    const user = userEvent.setup();
    renderTab();
    const schema = screen.getByRole("region", { name: "Schema" });
    await user.click(await within(schema).findByRole("button", { name: /^v0(?!\d)/ }));
    expect(screen.getByTestId("location")).toHaveTextContent("?schema=0");
    expect(await within(schema).findByRole("list", { name: "Changes in schema v0" })).toBeInTheDocument();
    expect(paths(calls)).toContain(`${TABLE}/schema-versions/0/comparison`);
  });

  it("compares with any other version and puts it in the url as base", async () => {
    const user = userEvent.setup();
    renderTab("?schema=0");
    const schema = screen.getByRole("region", { name: "Schema" });
    const compare = await within(schema).findByRole("combobox", { name: "Compare with" });
    expect(compare).toHaveTextContent("No earlier version");
    await user.click(compare);
    await user.click(await screen.findByRole("option", { name: "v1" }));
    expect(screen.getByTestId("location")).toHaveTextContent("?schema=0&base=1");
    await waitFor(() => expect(paths(calls)).toContain(`${TABLE}/schema-versions/0/comparison?base=1`));
    const list = await within(schema).findByRole("list", { name: "Changes in schema v0" });
    expect(within(list).getByText("coupon_code")).toBeInTheDocument();
    expect(within(list).getByText("Removed")).toBeInTheDocument();
  });

  it("names the previous version in the compare choices", async () => {
    const user = userEvent.setup();
    renderTab();
    const compare = await within(screen.getByRole("region", { name: "Schema" })).findByRole("combobox", {
      name: "Compare with",
    });
    expect(compare).toHaveTextContent("Previous version (v0)");
    await user.click(compare);
    expect((await screen.findAllByRole("option")).map((option) => option.textContent)).toEqual([
      "Previous version (v0)",
      "v0",
    ]);
  });

  it("hides unchanged rows with the switch and keeps the choice in the url", async () => {
    const user = userEvent.setup();
    renderTab();
    const schema = screen.getByRole("region", { name: "Schema" });
    const list = await within(schema).findByRole("list", { name: "Changes in schema v1" });
    expect(within(list).getByText("customer_id")).toBeInTheDocument();
    await user.click(within(schema).getByRole("switch", { name: "Show changes only" }));
    expect(screen.getByTestId("location")).toHaveTextContent("?only_changes=1");
    expect(within(list).queryByText("customer_id")).not.toBeInTheDocument();
    expect(within(list).getByText("order_id")).toBeInTheDocument();
  });

  it("shows nested fields with their full path and outer type", async () => {
    renderTab();
    const list = await within(screen.getByRole("region", { name: "Schema" })).findByRole("list", {
      name: "Changes in schema v1",
    });
    expect(within(list).getByText("address.zip")).toBeInTheDocument();
    expect(within(list).getByText("struct · optional")).toBeInTheDocument();
  });

  it("marks and opens on the current version when it is not the highest id", async () => {
    calls = stubSchemaTab({
      [`GET ${TABLE}/schema-versions`]: () =>
        jsonResponse({
          current_schema_id: 1,
          versions: [schemaVersion(2, { ...NONE, removed: 1 }), schemaVersion(1, { ...NONE, added: 5, doc_changed: 1 }, true), schemaVersion(0, null)],
        }),
    });
    renderTab();
    const schema = screen.getByRole("region", { name: "Schema" });
    await within(schema).findByRole("button", { name: /^v1(?!\d)/ });
    const buttons = within(schema).getAllByRole("button", { name: /^v\d/ });
    expect(buttons.map((button) => button.textContent?.slice(0, 2))).toEqual(["v2", "v1", "v0"]);
    expect(buttons[0]).not.toHaveTextContent("Current");
    expect(buttons[1]).toHaveTextContent("Current");
    expect(buttons[1]).toHaveAttribute("aria-current", "true");
    expect(await within(schema).findByRole("list", { name: "Changes in schema v1" })).toBeInTheDocument();
    expect(paths(calls)).not.toContain(`${TABLE}/schema-versions/2/comparison`);
  });

  it("opens on the current version when the url names one the table does not have", async () => {
    renderTab("?schema=9");
    const schema = screen.getByRole("region", { name: "Schema" });
    expect(
      await within(schema).findByText("Schema v9 is not in this table's history; showing the current schema (v1)."),
    ).toBeInTheDocument();
    expect(await within(schema).findByRole("list", { name: "Changes in schema v1" })).toBeInTheDocument();
    expect(paths(calls).some((path) => path.includes("/schema-versions/9/"))).toBe(false);
  });

  it("reads a url value that is not a number as no choice, without a line about it", async () => {
    renderTab("?schema=abc");
    const schema = screen.getByRole("region", { name: "Schema" });
    expect(await within(schema).findByRole("list", { name: "Changes in schema v1" })).toBeInTheDocument();
    expect(within(schema).queryByText(/is not in this table's history/)).not.toBeInTheDocument();
    expect(paths(calls).some((path) => path.includes("abc"))).toBe(false);
  });

  it("says what could not be loaded", async () => {
    calls = stubSchemaTab({ [`GET ${TABLE}/schema-versions`]: () => jsonResponse({ detail: "Polaris is down" }, 502) });
    renderTab();
    expect(
      await within(screen.getByRole("region", { name: "Schema" })).findByText(
        "Could not load schema versions: Polaris is down",
      ),
    ).toBeInTheDocument();
  });

  describe("partition spec", () => {
    it("marks the default spec and writes a transform change as before and after", async () => {
      renderTab();
      const spec = screen.getByRole("region", { name: "Partition spec" });
      const newest = await within(spec).findByRole("button", { name: /^v1/ });
      expect(newest).toHaveTextContent("Default");
      expect(newest).toHaveTextContent("1 transform changed");
      const list = await within(spec).findByRole("list", { name: "Changes in partition spec v1" });
      const row = within(list).getByText("order_ts_hour").closest("li") as HTMLElement;
      expect(row).toHaveTextContent("Transform changed");
      expect(row).toHaveTextContent("day(order_ts)");
      expect(row).toHaveTextContent("hour(order_ts)");
      expect(paths(calls)).toContain(`${TABLE}/partition-spec-versions/1/comparison`);
    });

    it("keeps the spec choice in its own url parameters", async () => {
      const user = userEvent.setup();
      renderTab("?schema=0");
      const spec = screen.getByRole("region", { name: "Partition spec" });
      await user.click(await within(spec).findByRole("button", { name: /^v0(?!\d)/ }));
      expect(screen.getByTestId("location")).toHaveTextContent("?schema=0&spec=0");
      await user.click(within(spec).getByRole("switch", { name: "Show changes only" }));
      expect(screen.getByTestId("location")).toHaveTextContent("?schema=0&spec=0&spec_only_changes=1");
    });

    it("says an unpartitioned table is unpartitioned", async () => {
      calls = stubSchemaTab({
        [`GET ${TABLE}/partition-spec-versions`]: () =>
          jsonResponse({
            default_spec_id: 0,
            versions: [{ spec_id: 0, previous_spec_id: null, default: true, field_count: 0, changes: null }],
          }),
        [`GET ${TABLE}/partition-spec-versions/0/comparison`]: () =>
          jsonResponse({ spec_id: 0, base_spec_id: null, fields: [] }),
      });
      renderTab();
      expect(
        await within(screen.getByRole("region", { name: "Partition spec" })).findByText("Unpartitioned."),
      ).toBeInTheDocument();
    });
  });

  it("builds the DDL from the current schema and says so", async () => {
    renderTab();
    const ddl = screen.getByRole("region", { name: "DDL (Spark SQL)" });
    expect(ddl).toHaveTextContent("Built from the current schema (v1); earlier versions have no DDL here.");
    expect(ddl).toHaveTextContent("CREATE TABLE `iceberg`.`retail`.`orders`");
    await screen.findByRole("region", { name: "Sort order" });
  });
});
