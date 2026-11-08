import type { Decorator, Preview } from "@storybook/react-vite";
import "../src/styles/index.css";
import { applyTheme } from "../src/theme/applyTheme";
import { DEFAULT_THEME, THEMES, type ThemeName } from "../src/theme/themes";

const withTheme: Decorator = (Story, context) => {
  applyTheme(document.documentElement, context.globals.theme as ThemeName);
  return (
    <div className="bg-surface font-sans text-on-surface">
      <Story />
    </div>
  );
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
  initialGlobals: {
    theme: DEFAULT_THEME,
  },
  decorators: [withTheme],
  parameters: {
    viewport: {
      options: {
        phone: { name: "Phone", styles: { width: "390px", height: "844px" }, type: "mobile" },
        desktop: { name: "Desktop", styles: { width: "1280px", height: "800px" }, type: "desktop" },
      },
    },
    a11y: {
      test: "error",
    },
  },
};

export default preview;
