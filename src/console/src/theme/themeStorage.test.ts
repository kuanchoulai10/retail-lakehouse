import { afterEach, describe, expect, it, vi } from "vitest";
import { readThemeChoice, writeThemeChoice } from "./themeStorage";

describe("themeStorage", () => {
  afterEach(() => {
    localStorage.clear();
  });

  it("reads system when nothing is stored", () => {
    expect(readThemeChoice()).toBe("system");
  });

  it("reads system when the stored value is not a theme choice", () => {
    localStorage.setItem("console-theme", "blue");
    expect(readThemeChoice()).toBe("system");
  });

  it("reads a stored choice", () => {
    localStorage.setItem("console-theme", "light");
    expect(readThemeChoice()).toBe("light");
  });

  it("reads system when localStorage throws", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(readThemeChoice()).toBe("system");
  });

  it("writes the choice under console-theme", () => {
    writeThemeChoice("dark");
    expect(localStorage.getItem("console-theme")).toBe("dark");
  });

  it("does not throw when localStorage refuses the write", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("quota");
    });
    expect(() => writeThemeChoice("dark")).not.toThrow();
  });
});
