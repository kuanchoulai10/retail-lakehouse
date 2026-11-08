export type ThemeName = "konjo" | "asagi" | "kurikawa";

export const THEMES: readonly { name: ThemeName; label: string }[] = [
  { name: "konjo", label: "Konjo" },
  { name: "asagi", label: "Asagi" },
  { name: "kurikawa", label: "Kurikawa" },
];

export const DEFAULT_THEME: ThemeName = "konjo";

export const THEME_STORAGE_KEY = "ds-theme";

export const THEME_ATTRIBUTE = "data-panda-theme";
