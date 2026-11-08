import { DEFAULT_THEME, THEME_ATTRIBUTE, type ThemeName } from "./themes";

export function applyTheme(root: HTMLElement, theme: ThemeName): void {
  if (theme === DEFAULT_THEME) {
    root.removeAttribute(THEME_ATTRIBUTE);
  } else {
    root.setAttribute(THEME_ATTRIBUTE, theme);
  }
}
