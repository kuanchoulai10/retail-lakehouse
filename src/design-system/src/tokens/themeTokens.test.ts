import { THEMES } from "../theme/themes";
import { contrastRatio } from "./contrastRatio";
import { resolveThemeTokens } from "./resolveThemeTokens";
import { CONTRAST_PAIRS, SEMANTIC_TOKENS, type SemanticToken } from "./semanticTokens";

const CHART_TOKENS: SemanticToken[] = ["chart-1", "chart-2", "chart-3", "chart-4", "chart-5"];
const STATUS_TOKENS: SemanticToken[] = ["positive-text", "notice-text", "negative-text", "negative"];

describe.each(THEMES.map((t) => t.name))("%s", (theme) => {
  const tokens = resolveThemeTokens(theme);
  it("defines every semantic token as a colour", () => {
    for (const name of SEMANTIC_TOKENS) expect(tokens[name]).toMatch(/^#[0-9A-F]{6}([0-9A-F]{2})?$/);
  });
  it("gives the chart series five distinct colours, none of them a status colour", () => {
    const series = CHART_TOKENS.map((name) => tokens[name]);
    const statuses = STATUS_TOKENS.map((name) => tokens[name]);
    expect(new Set(series).size).toBe(series.length);
    for (const colour of series) expect(statuses).not.toContain(colour);
  });
  it.each(CONTRAST_PAIRS)("$foreground on $background meets $minimum:1", ({ foreground, background, minimum }) => {
    expect(contrastRatio(tokens[foreground], tokens[background])).toBeGreaterThanOrEqual(minimum);
  });
});

it("themes really differ", () => {
  expect(resolveThemeTokens("asagi").primary).not.toBe(resolveThemeTokens("konjo").primary);
  expect(resolveThemeTokens("kurikawa").primary).toBe("#8F3D15");
});

it("lets the first chart series follow the theme and keeps the others the same in every theme", () => {
  const [konjo, asagi] = [resolveThemeTokens("konjo"), resolveThemeTokens("asagi")];
  expect(asagi["chart-1"]).not.toBe(konjo["chart-1"]);
  for (const name of CHART_TOKENS.slice(1)) expect(asagi[name]).toBe(konjo[name]);
});
