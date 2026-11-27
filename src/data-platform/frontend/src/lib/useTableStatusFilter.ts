import { useSearchParams } from "react-router";

export const TABLE_STATUSES = ["managed", "unmanaged", "undecided", "dropped"] as const;
export type TableStatus = (typeof TABLE_STATUSES)[number];

const PARAM = "status";
// Every live table: an undecided one has a policy attached to it, so it is not hidden.
const DEFAULT_STATUSES: readonly TableStatus[] = ["managed", "unmanaged", "undecided"];

function isDefault(statuses: readonly TableStatus[]): boolean {
  return statuses.length === DEFAULT_STATUSES.length && DEFAULT_STATUSES.every((s) => statuses.includes(s));
}

// No parameter, or one that names no known status, is the default; `?status=` is an explicit "none".
function parseStatuses(raw: string | null): readonly TableStatus[] {
  if (raw === null) return DEFAULT_STATUSES;
  if (raw === "") return [];
  const named = raw.split(",");
  const known = TABLE_STATUSES.filter((status) => named.includes(status));
  return known.length === 0 ? DEFAULT_STATUSES : known;
}

// The Tables page's status filter, kept in the url so a filtered list survives a reload and can be shared.
export function useTableStatusFilter(): {
  statuses: readonly TableStatus[];
  setStatuses: (statuses: readonly string[]) => void;
} {
  const [searchParams, setSearchParams] = useSearchParams();
  const statuses = parseStatuses(searchParams.get(PARAM));

  const setStatuses = (next: readonly string[]) => {
    const chosen = TABLE_STATUSES.filter((status) => next.includes(status));
    setSearchParams(
      (current) => {
        const params = new URLSearchParams(current);
        if (isDefault(chosen)) params.delete(PARAM);
        else params.set(PARAM, chosen.join(","));
        return params;
      },
      { replace: true },
    );
  };

  return { statuses, setStatuses };
}
