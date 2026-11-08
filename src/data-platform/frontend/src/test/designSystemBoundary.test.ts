const sources = import.meta.glob<string>(
  ["../**/*.{ts,tsx,css}", "!../**/*.test.{ts,tsx}", "!../test/**"],
  { query: "?raw", import: "default", eager: true },
);

const RAW_HEX = /#[0-9a-fA-F]{3,8}\b/;
const ARBITRARY_COLOUR = /\[#/;
const FUNCTIONAL_COLOUR = /\b(?:rgba?|hsla?|oklch|oklab|lab|lch|color-mix)\(/;
const PALETTE_COLOUR =
  /\b(?:bg|text|border(?:-[xytrblse])?|ring(?:-offset)?|inset-ring|fill|stroke|from|via|to|outline|divide|decoration|shadow|inset-shadow|drop-shadow|accent|caret|placeholder)-(?:red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|slate|gray|zinc|neutral|stone|black|white)(?:-\d{2,3})?\b/;
const SD_TOKEN = /--sd-/;
const FORBIDDEN_PACKAGE = /["'`](?:radix-ui|@radix-ui\/|lucide-react|@serendie\/)/;
const DESIGN_SYSTEM_DEEP_IMPORT =
  /["'`](?:@retail-lakehouse\/design-system\/(?!styles\.css["'`])|(?:\.\.\/)+design-system)/;
const SHADCN_COLOUR_UTILITY =
  /(?<![\w-])(?:bg|text|border|ring|outline|fill|stroke|divide|from|via|to)-(?:background|foreground|card|card-foreground|popover|popover-foreground|primary-foreground|secondary|secondary-foreground|muted|muted-foreground|accent-foreground|destructive|warning|success|border|input|ring|sidebar[\w-]*)(?![\w-])/;
const DARK_VARIANT = /(?<![\w-])dark:|@custom-variant dark/;

const RULES: Record<string, RegExp[]> = {
  "raw colours (hex, functional, arbitrary or Tailwind palette)": [
    RAW_HEX,
    FUNCTIONAL_COLOUR,
    ARBITRARY_COLOUR,
    PALETTE_COLOUR,
  ],
  "Serendie tokens (--sd-*)": [SD_TOKEN],
  "radix-ui, lucide-react or @serendie imports": [FORBIDDEN_PACKAGE],
  "design-system imports other than @retail-lakehouse/design-system": [DESIGN_SYSTEM_DEEP_IMPORT],
  "old shadcn colour utilities": [SHADCN_COLOUR_UTILITY],
  "dark mode variants": [DARK_VARIANT],
};

function offendersOf(patterns: RegExp[]): string[] {
  return Object.entries(sources).flatMap(([path, source]) =>
    source
      .split("\n")
      .map((line, index) => ({ line, index }))
      .filter(({ line }) => patterns.some((pattern) => pattern.test(line)))
      .map(({ line, index }) => `${path}:${index + 1}: ${line.trim()}`),
  );
}

describe("design-system boundary", () => {
  it("finds the console sources", () => {
    const paths = Object.keys(sources);
    expect(paths.some((p) => p.startsWith("../components/"))).toBe(true);
    expect(paths.some((p) => p.startsWith("../pages/"))).toBe(true);
    expect(paths.some((p) => p.endsWith(".css"))).toBe(true);
    expect(paths.some((p) => p.includes(".test."))).toBe(false);
    expect(paths.some((p) => p.startsWith("../test/"))).toBe(false);
  });

  it("detects raw and arbitrary colours", () => {
    expect(RAW_HEX.test('style={{ color: "#a35200" }}')).toBe(true);
    expect(ARBITRARY_COLOUR.test('className="bg-[#fafafa]"')).toBe(true);
    expect(PALETTE_COLOUR.test('className="text-red-600"')).toBe(true);
    expect(PALETTE_COLOUR.test('className="hover:bg-amber-100"')).toBe(true);
    expect(PALETTE_COLOUR.test('className="text-negative-text bg-surface"')).toBe(false);
    expect(PALETTE_COLOUR.test('className="border-t-red-500"')).toBe(true);
    expect(PALETTE_COLOUR.test('className="border-x-slate-200"')).toBe(true);
    expect(PALETTE_COLOUR.test('className="ring-offset-white"')).toBe(true);
    expect(PALETTE_COLOUR.test('className="outline-blue-500"')).toBe(true);
    expect(PALETTE_COLOUR.test('className="border-t-outline-dim ring-offset-surface"')).toBe(false);
  });

  it("detects functional colours", () => {
    for (const value of [
      'style={{ color: "rgb(0 0 0)" }}',
      'fill="rgba(0,0,0,0.5)"',
      "background: hsl(0 0% 100%);",
      "background: hsla(0, 0%, 100%, 0.5);",
      "color: oklch(0.6 0.1 200);",
      "color: oklab(0.6 0.1 0.1);",
      "color: lab(50% 40 59);",
      "color: lch(50% 40 59);",
      "color: color-mix(in srgb, currentColor, transparent);",
    ]) {
      expect(FUNCTIONAL_COLOUR.test(value)).toBe(true);
    }
    expect(FUNCTIONAL_COLOUR.test('<Label(htmlFor="x") className="bg-surface" />')).toBe(false);
  });

  it("detects forbidden packages, tokens and deep imports", () => {
    expect(SD_TOKEN.test("color: var(--sd-system-color-primary)")).toBe(true);
    expect(FORBIDDEN_PACKAGE.test('import { Dialog } from "radix-ui";')).toBe(true);
    expect(FORBIDDEN_PACKAGE.test("import { X } from '@radix-ui/react-dialog';")).toBe(true);
    expect(FORBIDDEN_PACKAGE.test('import { X } from "lucide-react";')).toBe(true);
    expect(FORBIDDEN_PACKAGE.test('import { X } from "@serendie/symbols";')).toBe(true);
    expect(FORBIDDEN_PACKAGE.test('import { Button } from "@retail-lakehouse/design-system";')).toBe(false);
    expect(DESIGN_SYSTEM_DEEP_IMPORT.test('from "@retail-lakehouse/design-system/src/index";')).toBe(true);
    expect(DESIGN_SYSTEM_DEEP_IMPORT.test('from "../../../design-system/src/index";')).toBe(true);
    expect(DESIGN_SYSTEM_DEEP_IMPORT.test('from "@retail-lakehouse/design-system";')).toBe(false);
    expect(DESIGN_SYSTEM_DEEP_IMPORT.test('@import "@retail-lakehouse/design-system/styles.css";')).toBe(false);
  });

  it("detects backtick-quoted forbidden packages and deep imports", () => {
    expect(FORBIDDEN_PACKAGE.test("const module = await import(`radix-ui`);")).toBe(true);
    expect(FORBIDDEN_PACKAGE.test("vi.mock(`@serendie/symbols`);")).toBe(true);
    expect(DESIGN_SYSTEM_DEEP_IMPORT.test("await import(`@retail-lakehouse/design-system/src/index`);")).toBe(true);
    expect(DESIGN_SYSTEM_DEEP_IMPORT.test("await import(`../../../design-system/src/index`);")).toBe(true);
    expect(DESIGN_SYSTEM_DEEP_IMPORT.test("await import(`@retail-lakehouse/design-system`);")).toBe(false);
    expect(DESIGN_SYSTEM_DEEP_IMPORT.test("import(`@retail-lakehouse/design-system/styles.css`);")).toBe(false);
  });

  it("detects old shadcn colour utilities and dark variants", () => {
    for (const utility of [
      "bg-background",
      "text-muted-foreground",
      "hover:text-foreground",
      "bg-card",
      "text-destructive",
      "border-border",
      "outline-ring/50",
      "bg-primary-foreground",
    ]) {
      expect(SHADCN_COLOUR_UTILITY.test(`className="${utility}"`)).toBe(true);
    }
    for (const utility of ["bg-surface", "text-on-surface-variant", "border-outline", "text-negative-text", "bg-primary"]) {
      expect(SHADCN_COLOUR_UTILITY.test(`className="${utility}"`)).toBe(false);
    }
    expect(DARK_VARIANT.test('className="dark:bg-input/30"')).toBe(true);
    expect(DARK_VARIANT.test("@custom-variant dark (&:is(.dark *));")).toBe(true);
    expect(DARK_VARIANT.test('className="bg-surface"')).toBe(false);
  });

  for (const [rule, patterns] of Object.entries(RULES)) {
    it(`has no ${rule} in console sources`, () => {
      expect(offendersOf(patterns)).toEqual([]);
    });
  }

  it("has no legacy stylesheet", () => {
    expect(Object.keys(sources).filter((p) => p === "../styles.css")).toEqual([]);
  });
});
