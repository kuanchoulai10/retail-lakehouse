import type { DateRange } from "@retail-lakehouse/design-system";
import { useSearchParams } from "react-router";
import { ListTableCommitsWriter, type ListTableCommitsParams } from "@/api/generated/model";

type Writer = NonNullable<ListTableCommitsWriter>;

const WRITERS = Object.values(ListTableCommitsWriter) as Writer[];

// Days travel in the url as the viewer's local calendar day, YYYY-MM-DD, as GitHub's
// ?since=&until= do; the request turns them into instants at local midnight.
function parseDay(value: string | null): Date | undefined {
  const match = value?.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return undefined;
  const [, year, month, day] = match.map(Number) as [number, number, number, number];
  return new Date(year, month - 1, day);
}

function formatDay(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function nextDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + 1);
}

function parseWriter(value: string | null): Writer | undefined {
  return WRITERS.find((writer) => writer === value);
}

export type CommitFilters = {
  range: DateRange | undefined;
  writer: Writer | undefined;
  isFiltered: boolean;
  params: ListTableCommitsParams;
  setRange: (range: DateRange | undefined) => void;
  setWriter: (writer: Writer | undefined) => void;
};

// The Commits tab's filters, kept in the url so a filtered history can be shared and survives a reload.
export function useCommitFilters(): CommitFilters {
  const [searchParams, setSearchParams] = useSearchParams();
  const from = parseDay(searchParams.get("since"));
  const until = parseDay(searchParams.get("until"));
  const range = from ? { from, to: until } : undefined;
  const writer = parseWriter(searchParams.get("writer"));

  const update = (changes: Record<string, string | undefined>) =>
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current);
        for (const [key, value] of Object.entries(changes)) {
          if (value === undefined) next.delete(key);
          else next.set(key, value);
        }
        return next;
      },
      { replace: true },
    );

  const params: ListTableCommitsParams = {
    ...(from && { since: from.toISOString() }),
    ...(until && { before: nextDay(until).toISOString() }),
    ...(writer && { writer }),
  };

  return {
    range,
    writer,
    isFiltered: range !== undefined || writer !== undefined,
    params,
    setRange: (next) =>
      update({ since: next ? formatDay(next.from) : undefined, until: next?.to ? formatDay(next.to) : undefined }),
    setWriter: (next) => update({ writer: next }),
  };
}
