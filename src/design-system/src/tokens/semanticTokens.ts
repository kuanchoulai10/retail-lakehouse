export type SemanticToken =
  | "surface"
  | "surface-container"
  | "surface-container-dim"
  | "on-surface"
  | "on-surface-variant"
  | "outline"
  | "outline-dim"
  | "primary"
  | "on-primary"
  | "primary-container"
  | "on-primary-container"
  | "hovered"
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
  "on-surface",
  "on-surface-variant",
  "outline",
  "outline-dim",
  "primary",
  "on-primary",
  "primary-container",
  "on-primary-container",
  "hovered",
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
  { foreground: "on-positive-container", background: "positive-container", minimum: 4.5 },
  { foreground: "on-notice-container", background: "notice-container", minimum: 4.5 },
  { foreground: "on-negative-container", background: "negative-container", minimum: 4.5 },
  { foreground: "positive-text", background: "surface", minimum: 4.5 },
  { foreground: "notice-text", background: "surface", minimum: 4.5 },
  { foreground: "negative-text", background: "surface", minimum: 4.5 },
  { foreground: "focus-ring", background: "surface", minimum: 3 },
  { foreground: "outline-dim", background: "surface", minimum: 3 },
];
