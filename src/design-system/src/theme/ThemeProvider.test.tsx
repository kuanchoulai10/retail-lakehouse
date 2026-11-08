import { act, render, renderHook, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "./ThemeProvider";
import { useTheme } from "./useTheme";

function Consumer() {
  const { theme, setTheme } = useTheme();
  return (
    <button onClick={() => setTheme("kurikawa")} type="button">
      {theme}
    </button>
  );
}

describe("ThemeProvider", () => {
  afterEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-panda-theme");
  });

  it("applies and persists the chosen theme", async () => {
    render(
      <ThemeProvider>
        <Consumer />
      </ThemeProvider>,
    );
    expect(document.documentElement.hasAttribute("data-panda-theme")).toBe(false);
    await act(async () => {
      screen.getByRole("button").click();
    });
    expect(document.documentElement.getAttribute("data-panda-theme")).toBe("kurikawa");
    expect(localStorage.getItem("ds-theme")).toBe("kurikawa");
    expect(screen.getByRole("button").textContent).toBe("kurikawa");
  });

  it("starts from the stored theme", () => {
    localStorage.setItem("ds-theme", "asagi");
    render(
      <ThemeProvider>
        <Consumer />
      </ThemeProvider>,
    );
    expect(document.documentElement.getAttribute("data-panda-theme")).toBe("asagi");
  });

  it("throws outside the provider", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => renderHook(() => useTheme())).toThrow("useTheme must be used inside ThemeProvider");
  });
});
