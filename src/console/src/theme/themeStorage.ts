export type ThemeChoice = "light" | "dark" | "system";

export const THEME_STORAGE_KEY = "console-theme";

const CHOICES: readonly ThemeChoice[] = ["light", "dark", "system"];

function isThemeChoice(value: unknown): value is ThemeChoice {
  return typeof value === "string" && (CHOICES as readonly string[]).includes(value);
}

export function readThemeChoice(): ThemeChoice {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    return isThemeChoice(stored) ? stored : "system";
  } catch {
    return "system";
  }
}

export function writeThemeChoice(choice: ThemeChoice): void {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, choice);
  } catch {
    // Storage can be blocked (private mode, site data off); the choice then lasts for this page.
  }
}
