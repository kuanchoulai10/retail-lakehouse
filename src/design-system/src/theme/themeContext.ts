import { createContext } from "react";
import type { ThemeName } from "./themes";

export interface ThemeContextValue {
  theme: ThemeName;
  setTheme(theme: ThemeName): void;
}

export const ThemeContext = createContext<ThemeContextValue | null>(null);
