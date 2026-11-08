import { THEME_STORAGE_KEY } from "@retail-lakehouse/design-system";
import { afterEach, describe, expect, it, vi } from "vitest";
import indexHtml from "../index.html?raw";

const THEME_ATTRIBUTE = "data-panda-theme";

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

  it.each(["asagi", "kurikawa"])("applies the stored %s theme to <html>", (theme) => {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
    runBootScript();
    expect(document.documentElement).toHaveAttribute(THEME_ATTRIBUTE, theme);
  });

  it.each(["konjo", "dark", "light", "system", "ASAGI", ""])(
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
