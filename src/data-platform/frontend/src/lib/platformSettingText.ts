import type { PlatformSettingApiResponse } from "@/api/generated/model";
import { formatBytes, formatCount, formatGbHours, formatSeconds } from "@/format";

export interface PlatformSettingText {
  value: string;
  // The exact amount, when the value is shown in a larger unit; null when the value already is exact.
  exact: string | null;
}

function secondsText(seconds: number): PlatformSettingText {
  const value = formatSeconds(seconds);
  if (value.endsWith(" s")) return { value: `${formatCount(seconds)} seconds`, exact: null };
  return { value, exact: `${formatCount(seconds)} seconds` };
}

function bytesText(bytes: number): PlatformSettingText {
  if (bytes < 1024) return { value: `${formatCount(bytes)} bytes`, exact: null };
  return { value: formatBytes(bytes), exact: `${formatCount(bytes)} bytes` };
}

// A platform setting's value in words: seconds and bytes in a larger unit with the exact amount kept
// beside them, a count before its unit, and a value that carries its own unit (768m) as it is.
export function platformSettingText({ value, unit }: PlatformSettingApiResponse): PlatformSettingText {
  if (typeof value === "string") return { value, exact: null };
  if (unit === "seconds") return secondsText(value);
  if (unit === "bytes") return bytesText(value);
  if (unit === "GB·hours") return { value: `${formatGbHours(value)} GB·hours`, exact: null };
  const amount = formatCount(value);
  return { value: unit === null ? amount : `${amount} ${unit}`, exact: null };
}
