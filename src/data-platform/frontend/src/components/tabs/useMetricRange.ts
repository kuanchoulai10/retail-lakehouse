import { useSearchParams } from "react-router";
import { GetTableMetricTrendsRange } from "@/api/generated/model";

const PARAM = "range";
const DEFAULT_RANGE: GetTableMetricTrendsRange = "6h";
const RANGES = Object.values(GetTableMetricTrendsRange);

function parseRange(raw: string | null): GetTableMetricTrendsRange {
  return RANGES.find((range) => range === raw) ?? DEFAULT_RANGE;
}

// The Overview's trend window, kept in the url so a chosen range survives a reload and can be shared;
// a missing or unknown `?range=` is the default, and choosing the default keeps the url clean.
export function useMetricRange(): {
  range: GetTableMetricTrendsRange;
  setRange: (next: string) => void;
} {
  const [searchParams, setSearchParams] = useSearchParams();
  const range = parseRange(searchParams.get(PARAM));

  const setRange = (next: string) => {
    const chosen = parseRange(next);
    setSearchParams(
      (current) => {
        const params = new URLSearchParams(current);
        if (chosen === DEFAULT_RANGE) params.delete(PARAM);
        else params.set(PARAM, chosen);
        return params;
      },
      { replace: true },
    );
  };

  return { range, setRange };
}
