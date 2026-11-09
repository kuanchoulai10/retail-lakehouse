import type { StorybookConfig } from "@storybook/react-vite";

const config: StorybookConfig = {
  stories: ["../src/**/*.stories.@(ts|tsx)"],
  addons: ["@storybook/addon-a11y", "@storybook/addon-vitest"],
  framework: "@storybook/react-vite",
  // Reachable from the owner's other devices through `tailscale serve`, and composed into
  // the console's Storybook.
  core: { allowedHosts: [".ts.net"] },
  // The console's Storybook shows these stories in an iframe from its tailnet origin, which
  // dev mode refuses by default (owner's call, 2026-11-09: only the tailnet and localhost
  // reach it).
  security: { insecureRemoteIframeEmbed: true, insecureIframeMessaging: true },
  viteFinal: (config) => ({ ...config, server: { ...config.server, allowedHosts: [".ts.net"] } }),
};

export default config;
