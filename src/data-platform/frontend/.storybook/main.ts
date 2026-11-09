import type { StorybookConfig } from "@storybook/react-vite";

const config: StorybookConfig = {
  stories: ["../src/**/*.stories.@(ts|tsx)"],
  addons: ["@storybook/addon-a11y", "@storybook/addon-vitest", "msw-storybook-addon"],
  framework: "@storybook/react-vite",
  // mockServiceWorker.js, from `msw init`: page stories answer the API through MSW.
  staticDirs: ["./public"],
  viteFinal: (config) => ({ ...config, base: "/" }),
};

export default config;
