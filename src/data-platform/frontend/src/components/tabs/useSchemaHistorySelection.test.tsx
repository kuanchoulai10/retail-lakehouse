import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter, useLocation, useNavigationType } from "react-router";
import { describe, expect, it } from "vitest";
import { useSchemaHistorySelection } from "./useSchemaHistorySelection";

// The hook together with where the router ended up and how it got there.
function useSelectionAndRoute() {
  const location = useLocation();
  return { selection: useSchemaHistorySelection(), search: location.search, navigationType: useNavigationType() };
}

function setup(search: string) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <MemoryRouter initialEntries={[`/tables/orders/schema${search}`]}>{children}</MemoryRouter>
  );
  return renderHook(useSelectionAndRoute, { wrapper });
}

describe("useSchemaHistorySelection", () => {
  it("reads a value that is not a non-negative integer as no choice", () => {
    const { result } = setup("?schema=abc&base=-1&spec=x&spec_base=1.5");
    expect(result.current.selection.schemaId).toBeUndefined();
    expect(result.current.selection.baseSchemaId).toBeUndefined();
    expect(result.current.selection.specId).toBeUndefined();
    expect(result.current.selection.baseSpecId).toBeUndefined();
  });

  it("reads non-negative integers, zero included, and the switches", () => {
    const { result } = setup("?schema=0&base=3&only_changes=1&spec=2&spec_base=0&spec_only_changes=1");
    const { selection } = result.current;
    expect([selection.schemaId, selection.baseSchemaId, selection.specId, selection.baseSpecId]).toEqual([0, 3, 2, 0]);
    expect([selection.schemaOnlyChanges, selection.specOnlyChanges]).toEqual([true, true]);
  });

  it("clears the base when a new schema version is chosen", () => {
    const { result } = setup("?schema=0&base=1");
    act(() => result.current.selection.setSchema(2));
    expect(result.current.search).toBe("?schema=2");
    expect(result.current.navigationType).toBe("REPLACE");
  });

  it("clears the base when a new partition spec version is chosen", () => {
    const { result } = setup("?spec=0&spec_base=1");
    act(() => result.current.selection.setSpec(2));
    expect(result.current.search).toBe("?spec=2");
    expect(result.current.navigationType).toBe("REPLACE");
  });

  it("drops a switch turned off and a base set back to the previous version", () => {
    const { result } = setup("?schema=0&base=1&only_changes=1&spec_only_changes=1");
    act(() => result.current.selection.setSchemaOnlyChanges(false));
    expect(result.current.search).toBe("?schema=0&base=1&spec_only_changes=1");
    expect(result.current.navigationType).toBe("REPLACE");
    act(() => result.current.selection.setSpecOnlyChanges(false));
    expect(result.current.search).toBe("?schema=0&base=1");
    act(() => result.current.selection.setBaseSchema(undefined));
    expect(result.current.search).toBe("?schema=0");
  });

  it("writes the base and the switches into the url, replacing the history entry", () => {
    const { result } = setup("");
    act(() => result.current.selection.setBaseSchema(1));
    expect(result.current.search).toBe("?base=1");
    act(() => result.current.selection.setSchemaOnlyChanges(true));
    act(() => result.current.selection.setBaseSpec(0));
    act(() => result.current.selection.setSpecOnlyChanges(true));
    expect(result.current.search).toBe("?base=1&only_changes=1&spec_base=0&spec_only_changes=1");
    expect(result.current.navigationType).toBe("REPLACE");
  });

  it("drops the spec base when the base is set back to the previous version", () => {
    const { result } = setup("?spec=1&spec_base=0");
    act(() => result.current.selection.setBaseSpec(undefined));
    expect(result.current.search).toBe("?spec=1");
  });
});
