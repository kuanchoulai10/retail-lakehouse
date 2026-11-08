import { afterEach, describe, expect, it, vi } from "vitest";
import { THEME_STORAGE_KEY } from "./themes";
import { readTheme, writeTheme } from "./themeStorage";
import { applyTheme } from "./applyTheme";

describe("theme runtime", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    document.documentElement.removeAttribute("data-panda-theme");
  });

  it.each([null, "dark", "system", "sumire", "KONJO"])("reads %s as konjo", (stored) => {
    if (stored === null) {
      localStorage.removeItem(THEME_STORAGE_KEY);
    } else {
      localStorage.setItem(THEME_STORAGE_KEY, stored);
    }
    expect(readTheme()).toBe("konjo");
  });

  it("reads a stored theme", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "kurikawa");
    expect(readTheme()).toBe("kurikawa");
  });

  it("falls back to konjo when storage throws", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(readTheme()).toBe("konjo");
  });

  it("writes under ds-theme", () => {
    writeTheme("asagi");
    expect(localStorage.getItem("ds-theme")).toBe("asagi");
  });

  it("survives a write that throws", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(() => writeTheme("asagi")).not.toThrow();
  });

  it("applies asagi as an attribute and konjo as none", () => {
    applyTheme(document.documentElement, "asagi");
    expect(document.documentElement.getAttribute("data-panda-theme")).toBe("asagi");
    applyTheme(document.documentElement, "konjo");
    expect(document.documentElement.hasAttribute("data-panda-theme")).toBe(false);
  });
});
