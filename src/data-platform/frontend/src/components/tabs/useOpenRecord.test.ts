import { act, renderHook } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { MemoryRouter, useLocation, useNavigationType } from "react-router";
import { describe, expect, it } from "vitest";
import { useOpenRecord } from "./useOpenRecord";

// The hook together with where the router ended up and how it got there.
function useRecordAndRoute() {
  const location = useLocation();
  return { record: useOpenRecord("run"), search: location.search, navigationType: useNavigationType() };
}

function setup(search: string) {
  const wrapper = ({ children }: { children: ReactNode }) =>
    createElement(MemoryRouter, { initialEntries: [`/t${search}`] }, children);
  return renderHook(useRecordAndRoute, { wrapper });
}

describe("useOpenRecord", () => {
  it("reads the open record's id from its parameter", () => {
    expect(setup("?run=mr-1").result.current.record.openId).toBe("mr-1");
    expect(setup("?since=x").result.current.record.openId).toBeNull();
  });

  it("opens a record by adding its parameter, keeping the others, with replace", () => {
    const { result } = setup("?since=x");
    act(() => result.current.record.open("mr-1"));
    expect(result.current.search).toBe("?since=x&run=mr-1");
    expect(result.current.navigationType).toBe("REPLACE");
    expect(result.current.record.openId).toBe("mr-1");
  });

  it("switches to another record in place", () => {
    const { result } = setup("?since=x&run=mr-1");
    act(() => result.current.record.open("mr-2"));
    expect(result.current.search).toBe("?since=x&run=mr-2");
  });

  it("closes by dropping only its parameter, with replace", () => {
    const { result } = setup("?since=x");
    act(() => result.current.record.open("mr-1"));
    act(() => result.current.record.close());
    expect(result.current.search).toBe("?since=x");
    expect(result.current.navigationType).toBe("REPLACE");
    expect(result.current.record.openId).toBeNull();
  });
});
