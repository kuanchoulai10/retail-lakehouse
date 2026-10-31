import { createContext } from "react";
import type { ThemeChoice } from "./themeStorage";

export type ResolvedTheme = "light" | "dark";

export interface ThemeContextValue {
  choice: ThemeChoice;
  resolved: ResolvedTheme;
  setChoice(choice: ThemeChoice): void;
}

export const ThemeContext = createContext<ThemeContextValue | null>(null);
