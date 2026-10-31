const featureSources = import.meta.glob<string>(
  ["../components/**/*.tsx", "!../components/ui/**", "../pages/**/*.tsx"],
  { query: "?raw", import: "default", eager: true },
);

const legacyStylesheet = import.meta.glob<string>("../styles.css", {
  query: "?raw",
  import: "default",
  eager: true,
});

const RAW_HEX = /#[0-9a-fA-F]{3,8}\b/;
const ARBITRARY_COLOUR = /\[#/;

describe("design tokens", () => {
  it("finds the feature sources", () => {
    const paths = Object.keys(featureSources);
    expect(paths.some((p) => p.startsWith("../components/"))).toBe(true);
    expect(paths.some((p) => p.startsWith("../pages/"))).toBe(true);
    expect(paths.some((p) => p.includes("/ui/"))).toBe(false);
  });

  it("detects raw and arbitrary colours", () => {
    expect(RAW_HEX.test('style={{ color: "#a35200" }}')).toBe(true);
    expect(ARBITRARY_COLOUR.test('className="bg-[#fafafa]"')).toBe(true);
    expect(RAW_HEX.test('className="text-muted-foreground"')).toBe(false);
  });

  it("uses token classes only in feature code", () => {
    const offenders = Object.entries(featureSources).flatMap(([path, source]) =>
      source
        .split("\n")
        .map((line, index) => ({ line, index }))
        .filter(({ line }) => RAW_HEX.test(line) || ARBITRARY_COLOUR.test(line))
        .map(({ line, index }) => `${path}:${index + 1}: ${line.trim()}`),
    );
    expect(offenders).toEqual([]);
  });

  it("has no legacy stylesheet", () => {
    expect(Object.keys(legacyStylesheet)).toEqual([]);
  });
});
