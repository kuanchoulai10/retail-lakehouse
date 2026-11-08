import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve as resolvePath } from "node:path";
import { fileURLToPath } from "node:url";
import type { ThemeName } from "../theme/themes";
import { SEMANTIC_TOKENS, type SemanticToken } from "./semanticTokens";

const tokensCss = readFileSync(
  createRequire(import.meta.url).resolve("@serendie/design-token/tokens.css"),
  "utf8",
);
const semanticCss = readFileSync(
  resolvePath(dirname(fileURLToPath(import.meta.url)), "../styles/semantic.css"),
  "utf8",
);

function declarations(css: string, selector: string): Map<string, string> {
  const start = css.indexOf(`${selector} {`);
  if (start < 0) throw new Error(`Selector not found: ${selector}`);
  const end = css.indexOf("}", start);
  const block = css.slice(css.indexOf("{", start) + 1, end);
  const map = new Map<string, string>();
  for (const match of block.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
    map.set(match[1]!, match[2]!.trim());
  }
  return map;
}

function resolve(value: string, scope: Map<string, string>): string {
  const ref = /^var\((--[\w-]+)\)$/.exec(value);
  if (!ref) return value;
  const next = scope.get(ref[1]!);
  if (next === undefined) throw new Error(`Unresolved token: ${ref[1]}`);
  return resolve(next, scope);
}

export function resolveThemeTokens(theme: ThemeName): Record<SemanticToken, string> {
  const scope = declarations(tokensCss, ":where(:root,:host)");
  if (theme !== "konjo") {
    for (const [key, value] of declarations(tokensCss, `[data-panda-theme=${theme}]`)) {
      scope.set(key, value);
    }
  }
  const semantic = declarations(semanticCss, ":root");
  const result = {} as Record<SemanticToken, string>;
  for (const name of SEMANTIC_TOKENS) {
    const value = semantic.get(`--ds-${name}`);
    if (value === undefined) throw new Error(`Missing semantic token: ${name}`);
    result[name] = resolve(value, scope).toUpperCase();
  }
  return result;
}
