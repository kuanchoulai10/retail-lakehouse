import { act, renderHook } from "@testing-library/react";
import { useMatchesMedia } from "./useMatchesMedia";

function fakeMediaQueryList(matches: boolean) {
  const listeners = new Set<() => void>();
  const list = {
    matches,
    addEventListener: (_type: string, listener: () => void) => listeners.add(listener),
    removeEventListener: (_type: string, listener: () => void) => listeners.delete(listener),
    fire(next: boolean) {
      list.matches = next;
      for (const listener of listeners) {
        listener();
      }
    },
  };
  return list;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useMatchesMedia", () => {
  it("follows the media query", () => {
    const mql = fakeMediaQueryList(false);
    const matchMedia = vi.fn().mockReturnValue(mql);
    vi.stubGlobal("matchMedia", matchMedia);
    const { result } = renderHook(() => useMatchesMedia("(min-width: 48rem)"));
    expect(matchMedia).toHaveBeenCalledWith("(min-width: 48rem)");
    expect(result.current).toBe(false);
    act(() => mql.fire(true));
    expect(result.current).toBe(true);
  });

  it("stops listening when unmounted", () => {
    const mql = fakeMediaQueryList(true);
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue(mql));
    const { unmount } = renderHook(() => useMatchesMedia("(min-width: 48rem)"));
    unmount();
    expect(() => act(() => mql.fire(false))).not.toThrow();
  });

  it("is true when matchMedia is missing", () => {
    vi.stubGlobal("matchMedia", undefined);
    const { result } = renderHook(() => useMatchesMedia("(min-width: 48rem)"));
    expect(result.current).toBe(true);
  });
});
