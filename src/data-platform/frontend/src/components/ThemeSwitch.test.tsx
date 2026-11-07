import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "../theme/ThemeProvider";
import { ThemeSwitch } from "./ThemeSwitch";

function mockPrefersDark(matches: boolean) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn((query: string) => ({
      matches: query === "(prefers-color-scheme: dark)" ? matches : false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  );
}

function renderSwitch() {
  return render(
    <ThemeProvider>
      <ThemeSwitch />
    </ThemeProvider>,
  );
}

async function choose(label: string) {
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: /theme/i }));
  await user.click(await screen.findByRole("menuitemradio", { name: label }));
}

describe("ThemeSwitch", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  afterEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  it("choosing Dark adds the dark class and stores the choice", async () => {
    mockPrefersDark(false);
    renderSwitch();
    await choose("Dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(localStorage.getItem("console-theme")).toBe("dark");
  });

  it("choosing System follows a dark operating system", async () => {
    mockPrefersDark(true);
    localStorage.setItem("console-theme", "light");
    renderSwitch();
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    await choose("System");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(localStorage.getItem("console-theme")).toBe("system");
  });

  it("choosing System follows a light operating system", async () => {
    mockPrefersDark(false);
    localStorage.setItem("console-theme", "dark");
    renderSwitch();
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    await choose("System");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});
