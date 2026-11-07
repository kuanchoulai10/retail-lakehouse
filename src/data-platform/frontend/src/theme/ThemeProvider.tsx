import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { ThemeContext, type ResolvedTheme } from "./themeContext";
import { readThemeChoice, writeThemeChoice, type ThemeChoice } from "./themeStorage";

const DARK_QUERY = "(prefers-color-scheme: dark)";

function darkMedia(): MediaQueryList | null {
  return typeof window.matchMedia === "function" ? window.matchMedia(DARK_QUERY) : null;
}

function readSystemDark(): boolean {
  return darkMedia()?.matches ?? false;
}

function ignoreSystem(): () => void {
  return () => {};
}

function followSystem(onChange: () => void): () => void {
  const media = darkMedia();
  if (!media) {
    return () => {};
  }
  media.addEventListener("change", onChange);
  return () => media.removeEventListener("change", onChange);
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [choice, setChoiceState] = useState<ThemeChoice>(readThemeChoice);
  const systemDark = useSyncExternalStore(
    choice === "system" ? followSystem : ignoreSystem,
    readSystemDark,
  );

  const resolved: ResolvedTheme = choice === "system" ? (systemDark ? "dark" : "light") : choice;

  useEffect(() => {
    document.documentElement.classList.toggle("dark", resolved === "dark");
  }, [resolved]);

  const setChoice = useCallback((next: ThemeChoice) => {
    writeThemeChoice(next);
    setChoiceState(next);
  }, []);

  const value = useMemo(() => ({ choice, resolved, setChoice }), [choice, resolved, setChoice]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
