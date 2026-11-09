import { DEFAULT_THEME, THEMES, type ThemeName, writeTheme } from "@retail-lakehouse/design-system";
import type { Decorator, Preview } from "@storybook/react-vite";
import { mswLoader } from "msw-storybook-addon/csf3";
import "../src/styles/globals.css";

// The console's ThemeProvider reads the stored theme when it mounts, so the toolbar stores it
// and remounts the story.
const withTheme: Decorator = (Story, context) => {
  const theme = context.globals.theme as ThemeName;
  writeTheme(theme);
  return <Story key={theme} />;
};

const preview: Preview = {
  globalTypes: {
    theme: {
      description: "Design-system theme",
      toolbar: {
        title: "Theme",
        icon: "paintbrush",
        items: THEMES.map((theme) => ({ value: theme.name, title: theme.label })),
        dynamicTitle: true,
      },
    },
  },
  initialGlobals: { theme: DEFAULT_THEME },
  // Page stories answer the API through MSW: each story adds its handlers in beforeEach.
  loaders: [mswLoader()],
  decorators: [withTheme],
  parameters: {
    layout: "fullscreen",
    viewport: {
      options: {
        phone: { name: "Phone", styles: { width: "390px", height: "844px" }, type: "mobile" },
        desktop: { name: "Desktop", styles: { width: "1280px", height: "800px" }, type: "desktop" },
      },
    },
    a11y: { test: "error" },
  },
};

export default preview;
