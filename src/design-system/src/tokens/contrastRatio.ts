function channels(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  const alpha = h.length === 8 ? parseInt(h.slice(6, 8), 16) / 255 : 1;
  const out = [0, 2, 4].map((i) => {
    const c = parseInt(h.slice(i, i + 2), 16);
    return c * alpha + 255 * (1 - alpha);
  });
  return [out[0]!, out[1]!, out[2]!];
}

function luminance(hex: string): number {
  const [r, g, b] = channels(hex).map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrastRatio(foreground: string, background: string): number {
  const a = luminance(foreground);
  const b = luminance(background);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}
