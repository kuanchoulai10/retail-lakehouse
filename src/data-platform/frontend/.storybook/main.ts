import type { StorybookConfig } from "@storybook/react-vite";

const config: StorybookConfig = {
  stories: ["../src/**/*.stories.@(ts|tsx)"],
  addons: ["@storybook/addon-a11y", "@storybook/addon-vitest", "msw-storybook-addon"],
  framework: "@storybook/react-vite",
  // mockServiceWorker.js, from `msw init`: page stories answer the API through MSW.
  staticDirs: ["./public"],
  // Reachable from the owner's other devices through `tailscale serve` (MagicDNS names).
  core: { allowedHosts: [".ts.net"] },
  viteFinal: (config) => ({
    ...config,
    base: "/",
    server: { ...config.server, allowedHosts: [".ts.net"] },
  }),
};

export default config;
