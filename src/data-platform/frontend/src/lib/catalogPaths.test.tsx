import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useParams } from "react-router";
import { describe, expect, it } from "vitest";
import { getDeleteCatalogUrl } from "@/api/generated/catalogs/catalogs";
import { getGetGenericTableUrl, getListGenericTablesUrl } from "@/api/generated/generic-tables/generic-tables";
import {
  getGetNamespaceUrl,
  getListNamespacesUrl,
  getUpdateNamespacePropertiesUrl,
} from "@/api/generated/namespaces/namespaces";
import { getGetCatalogTableUrl, getGetTableUrl, getListCatalogTablesUrl } from "@/api/generated/tables/tables";
import { getGetViewUrl, getListViewsUrl } from "@/api/generated/views/views";
import {
  apiNamespace,
  catalogPath,
  catalogsPath,
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
    expect(apiNamespace(["a.b", "c"])).toBe("a.b\u001fc");
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

// The generated client builds the API URLs; these pin how it encodes what apiNamespace joins.
describe("catalog API URLs", () => {
  it("sends a namespace's parts joined by %1F", () => {
    expect(getDeleteCatalogUrl("a b")).toBe("/v1/catalogs/a%20b");
    expect(getListNamespacesUrl("iceberg")).toBe("/v1/catalogs/iceberg/namespaces");
    expect(getListNamespacesUrl("iceberg", { parent: apiNamespace(["a.b", "c"]) })).toBe(
      "/v1/catalogs/iceberg/namespaces?parent=a.b%1Fc",
    );
    expect(getGetNamespaceUrl("iceberg", apiNamespace(["a.b", "c"]))).toBe(
      "/v1/catalogs/iceberg/namespaces/a.b%1Fc",
    );
    expect(getUpdateNamespacePropertiesUrl("iceberg", apiNamespace(["retail"]))).toBe(
      "/v1/catalogs/iceberg/namespaces/retail/properties",
    );
  });

  it("encodes the table, view and generic table names as one segment", () => {
    const ns = "/v1/catalogs/iceberg/namespaces/retail%1Feu";
    const parts = apiNamespace(["retail", "eu"]);
    expect(getListCatalogTablesUrl("iceberg", parts)).toBe(`${ns}/tables`);
    expect(getGetCatalogTableUrl("iceberg", parts, "a/b")).toBe(`${ns}/tables/a%2Fb`);
    expect(getListViewsUrl("iceberg", parts)).toBe(`${ns}/views`);
    expect(getGetViewUrl("iceberg", parts, "v")).toBe(`${ns}/views/v`);
    expect(getListGenericTablesUrl("iceberg", parts)).toBe(`${ns}/generic-tables`);
    expect(getGetGenericTableUrl("iceberg", parts, "g")).toBe(`${ns}/generic-tables/g`);
  });

  it("encodes the maintenance table's uuid as one segment", () => {
    expect(getGetTableUrl("uuid-orders")).toBe("/v1/tables/uuid-orders");
    expect(getGetTableUrl("a/b?c")).toBe("/v1/tables/a%2Fb%3Fc");
  });
});

describe("catalogsPath", () => {
  it("is the catalogs list that every catalog path starts from", () => {
    expect(catalogsPath()).toBe("/catalogs");
    expect(catalogPath("iceberg").startsWith(`${catalogsPath()}/`)).toBe(true);
  });
});
