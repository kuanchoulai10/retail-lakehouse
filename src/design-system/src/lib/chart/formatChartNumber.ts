const formatter = new Intl.NumberFormat("en", { maximumFractionDigits: 2 });

export function formatChartNumber(value: number): string {
  return formatter.format(value);
}
