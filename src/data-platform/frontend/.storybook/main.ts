import type { StorybookConfig } from "@storybook/react-vite";

const config: StorybookConfig = {
  stories: ["../src/**/*.stories.@(ts|tsx)"],
  addons: ["@storybook/addon-a11y", "@storybook/addon-vitest", "msw-storybook-addon"],
  framework: "@storybook/react-vite",
  // mockServiceWorker.js, from `msw init`: page stories answer the API through MSW.
  staticDirs: ["./public"],
  // The design system's own Storybook, shown in this sidebar; it must be running too. Set
  // DESIGN_SYSTEM_STORYBOOK_URL to its tailnet URL to browse both from another device.
  refs: {
    "design-system": {
      title: "Design system",
      url: process.env.DESIGN_SYSTEM_STORYBOOK_URL ?? "http://localhost:6006",
    },
  },
  // Reachable from the owner's other devices through `tailscale serve` (MagicDNS names).
  core: { allowedHosts: [".ts.net"] },
  viteFinal: (config) => ({
    ...config,
    base: "/",
    server: { ...config.server, allowedHosts: [".ts.net"] },
  }),
};

export default config;
