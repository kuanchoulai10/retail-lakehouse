const START = Date.UTC(2026, 10, 19, 6, 0);
const TEN_MINUTES = 10 * 60 * 1000;

export const SAMPLE_TIMES = Array.from({ length: 36 }, (_, step) => START + step * TEN_MINUTES);

export function formatSampleTime(value: unknown): string {
  const date = new Date(Number(value));
  return `${String(date.getUTCHours()).padStart(2, "0")}:${String(date.getUTCMinutes()).padStart(2, "0")}`;
}

export const FILE_COUNTS = SAMPLE_TIMES.map((time, step) => ({
  time,
  dataFiles: 1180 + step * 14 - (step >= 24 ? 520 : 0),
  positionDeletes: 42 + Math.round(step * 1.5) - (step >= 24 ? 40 : 0),
  equalityDeletes: 12 + (step % 6),
}));

export const TOTAL_BYTES = SAMPLE_TIMES.map((time, step) => ({
  time,
  bytes: 3.2e9 + step * 2.5e7,
}));

export const COMMITS_PER_HOUR = [
  { hour: "06:00", appends: 12, overwrites: 2 },
  { hour: "07:00", appends: 18, overwrites: 1 },
  { hour: "08:00", appends: 9, overwrites: 4 },
  { hour: "09:00", appends: 21, overwrites: 0 },
  { hour: "10:00", appends: 15, overwrites: 3 },
  { hour: "11:00", appends: 11, overwrites: 2 },
];

const BYTE_UNITS = ["B", "KB", "MB", "GB", "TB"];

export function formatBytes(value: number): string {
  let size = value;
  let unit = 0;
  while (size >= 1024 && unit < BYTE_UNITS.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(size >= 10 || unit === 0 ? 0 : 1)} ${BYTE_UNITS[unit]}`;
}
