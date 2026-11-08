import { THEMES } from "../theme/themes";
import { contrastRatio } from "./contrastRatio";
import { resolveThemeTokens } from "./resolveThemeTokens";
import { CONTRAST_PAIRS, SEMANTIC_TOKENS } from "./semanticTokens";

describe.each(THEMES.map((t) => t.name))("%s", (theme) => {
  const tokens = resolveThemeTokens(theme);
  it("defines every semantic token as a colour", () => {
    for (const name of SEMANTIC_TOKENS) expect(tokens[name]).toMatch(/^#[0-9A-F]{6}([0-9A-F]{2})?$/);
  });
  it.each(CONTRAST_PAIRS)("$foreground on $background meets $minimum:1", ({ foreground, background, minimum }) => {
    expect(contrastRatio(tokens[foreground], tokens[background])).toBeGreaterThanOrEqual(minimum);
  });
});

it("themes really differ", () => {
  expect(resolveThemeTokens("asagi").primary).not.toBe(resolveThemeTokens("konjo").primary);
  expect(resolveThemeTokens("kurikawa").primary).toBe("#8F3D15");
});
