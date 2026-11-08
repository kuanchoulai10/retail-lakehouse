import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { applyTheme } from "./applyTheme";
import { ThemeContext } from "./themeContext";
import { readTheme, writeTheme } from "./themeStorage";
import type { ThemeName } from "./themes";

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeName>(readTheme);

  useEffect(() => {
    applyTheme(document.documentElement, theme);
  }, [theme]);

  const setTheme = useCallback((next: ThemeName) => {
    writeTheme(next);
    setThemeState(next);
  }, []);

  const value = useMemo(() => ({ theme, setTheme }), [theme, setTheme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
