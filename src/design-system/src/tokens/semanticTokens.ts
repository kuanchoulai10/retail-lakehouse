export type SemanticToken =
  | "surface"
  | "surface-container"
  | "surface-container-dim"
  | "surface-container-bright"
  | "inverse-surface"
  | "inverse-on-surface"
  | "inverse-primary"
  | "on-surface"
  | "on-surface-variant"
  | "outline"
  | "outline-dim"
  | "primary"
  | "on-primary"
  | "primary-container"
  | "on-primary-container"
  | "hovered"
  | "hovered-variant"
  | "hovered-on-primary"
  | "selected-surface"
  | "disabled"
  | "on-disabled"
  | "scrim"
  | "focus-ring"
  | "positive-container"
  | "on-positive-container"
  | "positive-text"
  | "notice-container"
  | "on-notice-container"
  | "notice-text"
  | "negative"
  | "on-negative"
  | "negative-container"
  | "on-negative-container"
  | "negative-text"
  | "chart-1"
  | "chart-2"
  | "chart-3"
  | "chart-4"
  | "chart-5";

export const SEMANTIC_TOKENS: readonly SemanticToken[] = [
  "surface",
  "surface-container",
  "surface-container-dim",
  "surface-container-bright",
  "inverse-surface",
  "inverse-on-surface",
  "inverse-primary",
  "on-surface",
  "on-surface-variant",
  "outline",
  "outline-dim",
  "primary",
  "on-primary",
  "primary-container",
  "on-primary-container",
  "hovered",
  "hovered-variant",
  "hovered-on-primary",
  "selected-surface",
  "disabled",
  "on-disabled",
  "scrim",
  "focus-ring",
  "positive-container",
  "on-positive-container",
  "positive-text",
  "notice-container",
  "on-notice-container",
  "notice-text",
  "negative",
  "on-negative",
  "negative-container",
  "on-negative-container",
  "negative-text",
  "chart-1",
  "chart-2",
  "chart-3",
  "chart-4",
  "chart-5",
];

interface ContrastPair {
  foreground: SemanticToken;
  background: SemanticToken;
  minimum: 4.5 | 3;
}

export const CONTRAST_PAIRS: readonly ContrastPair[] = [
  { foreground: "on-surface", background: "surface", minimum: 4.5 },
  { foreground: "on-surface", background: "surface-container", minimum: 4.5 },
  { foreground: "on-surface-variant", background: "surface", minimum: 4.5 },
  { foreground: "on-surface-variant", background: "surface-container", minimum: 4.5 },
  { foreground: "on-primary", background: "primary", minimum: 4.5 },
  { foreground: "on-primary-container", background: "primary-container", minimum: 4.5 },
  { foreground: "primary", background: "surface", minimum: 4.5 },
  { foreground: "primary", background: "surface-container", minimum: 4.5 },
  { foreground: "primary", background: "surface-container-bright", minimum: 4.5 },
  { foreground: "on-surface", background: "surface-container-bright", minimum: 4.5 },
  { foreground: "on-surface", background: "selected-surface", minimum: 4.5 },
  { foreground: "primary", background: "selected-surface", minimum: 3 },
  { foreground: "on-surface", background: "inverse-primary", minimum: 4.5 },
  { foreground: "inverse-on-surface", background: "inverse-surface", minimum: 4.5 },
  { foreground: "on-positive-container", background: "positive-container", minimum: 4.5 },
  { foreground: "on-notice-container", background: "notice-container", minimum: 4.5 },
  { foreground: "on-negative", background: "negative", minimum: 4.5 },
  { foreground: "on-negative-container", background: "negative-container", minimum: 4.5 },
  { foreground: "positive-text", background: "surface", minimum: 4.5 },
  { foreground: "notice-text", background: "surface", minimum: 4.5 },
  { foreground: "negative-text", background: "surface", minimum: 4.5 },
  { foreground: "focus-ring", background: "surface", minimum: 3 },
  { foreground: "outline-dim", background: "surface", minimum: 3 },
  { foreground: "outline-dim", background: "surface-container", minimum: 3 },
  { foreground: "outline-dim", background: "surface-container-dim", minimum: 3 },
  { foreground: "chart-1", background: "surface-container", minimum: 3 },
  { foreground: "chart-2", background: "surface-container", minimum: 3 },
  { foreground: "chart-3", background: "surface-container", minimum: 3 },
  { foreground: "chart-4", background: "surface-container", minimum: 3 },
  { foreground: "chart-5", background: "surface-container", minimum: 3 },
  { foreground: "chart-5", background: "surface-container-dim", minimum: 3 },
];
