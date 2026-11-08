import {
  DEFAULT_THEME,
  THEME_ATTRIBUTE,
  THEME_STORAGE_KEY,
  THEMES,
} from "@retail-lakehouse/design-system";
import { afterEach, describe, expect, it, vi } from "vitest";
import indexHtml from "../index.html?raw";

function bootScript(): string {
  const doc = new DOMParser().parseFromString(indexHtml, "text/html");
  const inline = Array.from(doc.head.querySelectorAll("script")).filter(
    (script) => !script.hasAttribute("src"),
  );
  expect(inline).toHaveLength(1);
  return inline[0]!.textContent ?? "";
}

function runBootScript(): void {
  new Function(bootScript())();
}

afterEach(() => {
  document.documentElement.removeAttribute(THEME_ATTRIBUTE);
  document.documentElement.className = "";
  localStorage.clear();
});

describe("index.html theme boot script", () => {
  it("runs inline in the head, before the app module", () => {
    expect(bootScript()).not.toBe("");
  });

  it("reads the design-system theme storage key", () => {
    expect(bootScript()).toContain(`"${THEME_STORAGE_KEY}"`);
  });

  it("knows nothing about dark mode", () => {
    expect(bootScript()).not.toMatch(/dark/i);
  });

  // Driven from the design system's list, so a theme added there but missing from the boot script fails.
  const NON_DEFAULT_THEMES = THEMES.map((theme) => theme.name).filter((name) => name !== DEFAULT_THEME);

  it("covers at least one non-default theme", () => {
    expect(NON_DEFAULT_THEMES.length).toBeGreaterThan(0);
  });

  it.each(NON_DEFAULT_THEMES)("applies the stored %s theme to <html>", (theme) => {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
    runBootScript();
    expect(document.documentElement).toHaveAttribute(THEME_ATTRIBUTE, theme);
  });

  const UNKNOWN_VALUES = ["dark", "light", "system", ...NON_DEFAULT_THEMES.map((name) => name.toUpperCase()), ""];

  it.each([DEFAULT_THEME, ...UNKNOWN_VALUES])(
    "leaves the default theme with no attribute for a stored %j",
    (value) => {
      localStorage.setItem(THEME_STORAGE_KEY, value);
      runBootScript();
      expect(document.documentElement).not.toHaveAttribute(THEME_ATTRIBUTE);
      expect(document.documentElement).not.toHaveClass("dark");
    },
  );

  it("leaves the default theme when nothing is stored", () => {
    runBootScript();
    expect(document.documentElement).not.toHaveAttribute(THEME_ATTRIBUTE);
  });

  it("leaves the default theme, without throwing, when storage is blocked", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    expect(runBootScript).not.toThrow();
    expect(document.documentElement).not.toHaveAttribute(THEME_ATTRIBUTE);
  });
});
