import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useParams } from "react-router";
import { describe, expect, it } from "vitest";
import {
  apiNamespace,
  catalogPath,
  genericTablePath,
  namespaceFromParam,
  namespacePath,
  tablePath,
  viewPath,
} from "./catalogPaths";

function Probe() {
  const { namespace = "" } = useParams();
  return <p data-testid="parts">{JSON.stringify(namespaceFromParam(namespace))}</p>;
}

describe("catalogPaths", () => {
  it("namespace path with a dot part links and loads", () => {
    expect(apiNamespace(["a.b", "c"])).toBe("a.b%1Fc");
    const path = namespacePath("iceberg", ["a.b", "c"]);
    expect(path).toBe("/catalogs/iceberg/namespaces/a.b%1Fc");
    render(
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/catalogs/:catalog/namespaces/:namespace" element={<Probe />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("parts")).toHaveTextContent('["a.b","c"]');
  });

  it("encodes each name segment", () => {
    expect(catalogPath("my cat")).toBe("/catalogs/my%20cat");
    expect(apiNamespace(["a/b"])).toBe("a%2Fb");
  });

  it("builds object paths under the namespace", () => {
    expect(tablePath("c", ["n"], "t")).toBe("/catalogs/c/namespaces/n/tables/t");
    expect(tablePath("c", ["n"], "t", "schema")).toBe("/catalogs/c/namespaces/n/tables/t/schema");
    expect(viewPath("c", ["n"], "v")).toBe("/catalogs/c/namespaces/n/views/v");
    expect(genericTablePath("c", ["n"], "g")).toBe("/catalogs/c/namespaces/n/generic-tables/g");
  });
});
