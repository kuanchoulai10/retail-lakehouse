import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useParams } from "react-router";
import { describe, expect, it } from "vitest";
import {
  apiNamespace,
  catalogApiPath,
  catalogPath,
  catalogsApiPath,
  genericTableApiPath,
  genericTablesApiPath,
  namespaceApiPath,
  namespacePropertiesApiPath,
  namespacesApiPath,
  tableApiPath,
  tablesApiPath,
  viewApiPath,
  viewsApiPath,
  genericTablePath,
  namespaceFromParam,
  namespacePath,
  tablePath,
  viewPath,
} from "./catalogPaths";

function Probe() {
  const { catalog = "", namespace = "", name = "" } = useParams();
  return (
    <p data-testid="parts">
      {JSON.stringify({ catalog, namespace: namespaceFromParam(namespace), name })}
    </p>
  );
}

function routed(path: string, pattern: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path={pattern} element={<Probe />} />
      </Routes>
    </MemoryRouter>,
  );
  return JSON.parse(screen.getByTestId("parts").textContent ?? "{}");
}

const AWKWARD = "a/b c%d";

describe("catalogPaths", () => {
  it("namespace path with a dot part links and loads", () => {
    expect(apiNamespace(["a.b", "c"])).toBe("a.b%1Fc");
    const path = namespacePath("iceberg", ["a.b", "c"]);
    expect(path).toBe("/catalogs/iceberg/namespaces/a.b%1Fc");
    const parsed = routed(path, "/catalogs/:catalog/namespaces/:namespace");
    expect(parsed.namespace).toEqual(["a.b", "c"]);
  });

  it("round-trips a slash, a space and a percent in a catalog", () => {
    expect(routed(catalogPath(AWKWARD), "/catalogs/:catalog").catalog).toBe(AWKWARD);
  });

  it("round-trips a slash, a space and a percent in namespace parts", () => {
    const parsed = routed(
      namespacePath("c", [AWKWARD, "x.y"]),
      "/catalogs/:catalog/namespaces/:namespace",
    );
    expect(parsed.namespace).toEqual([AWKWARD, "x.y"]);
  });

  it.each([
    ["table", tablePath(AWKWARD, [AWKWARD], AWKWARD), "tables"],
    ["view", viewPath(AWKWARD, [AWKWARD], AWKWARD), "views"],
    ["generic table", genericTablePath(AWKWARD, [AWKWARD], AWKWARD), "generic-tables"],
  ])("round-trips awkward characters in a %s path", (_kind, path, segment) => {
    const parsed = routed(path, `/catalogs/:catalog/namespaces/:namespace/${segment}/:name`);
    expect(parsed).toEqual({ catalog: AWKWARD, namespace: [AWKWARD], name: AWKWARD });
  });

  it("appends the tab to a table path", () => {
    expect(tablePath("c", ["n"], "t")).toBe("/catalogs/c/namespaces/n/tables/t");
    expect(tablePath("c", ["n"], "t", "schema")).toBe("/catalogs/c/namespaces/n/tables/t/schema");
    expect(viewPath("c", ["n"], "v")).toBe("/catalogs/c/namespaces/n/views/v");
    expect(genericTablePath("c", ["n"], "g")).toBe("/catalogs/c/namespaces/n/generic-tables/g");
  });
});

describe("catalog API paths", () => {
  it("builds the catalog and namespace API paths", () => {
    expect(catalogsApiPath()).toBe("/v1/catalogs");
    expect(catalogApiPath("a b")).toBe("/v1/catalogs/a%20b");
    expect(namespacesApiPath("iceberg", [])).toBe("/v1/catalogs/iceberg/namespaces");
    expect(namespacesApiPath("iceberg", ["a.b", "c"])).toBe(
      "/v1/catalogs/iceberg/namespaces?parent=a.b%1Fc",
    );
    expect(namespaceApiPath("iceberg", ["a.b", "c"])).toBe("/v1/catalogs/iceberg/namespaces/a.b%1Fc");
    expect(namespacePropertiesApiPath("iceberg", ["retail"])).toBe(
      "/v1/catalogs/iceberg/namespaces/retail/properties",
    );
  });

  it("builds the table, view and generic table API paths", () => {
    const ns = "/v1/catalogs/iceberg/namespaces/retail%1Feu";
    expect(tablesApiPath("iceberg", ["retail", "eu"])).toBe(`${ns}/tables`);
    expect(tableApiPath("iceberg", ["retail", "eu"], "a/b")).toBe(`${ns}/tables/a%2Fb`);
    expect(viewsApiPath("iceberg", ["retail", "eu"])).toBe(`${ns}/views`);
    expect(viewApiPath("iceberg", ["retail", "eu"], "v")).toBe(`${ns}/views/v`);
    expect(genericTablesApiPath("iceberg", ["retail", "eu"])).toBe(`${ns}/generic-tables`);
    expect(genericTableApiPath("iceberg", ["retail", "eu"], "g")).toBe(`${ns}/generic-tables/g`);
  });
});
