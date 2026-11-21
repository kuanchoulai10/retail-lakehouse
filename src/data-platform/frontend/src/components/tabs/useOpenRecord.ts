import { useSearchParams } from "react-router";

// The record a tab shows in its side panel, kept in one search parameter so a link to it can be
// shared or reloaded. Opening, switching and closing replace the url entry: Back leaves the tab
// instead of stepping through every record opened. The tab's other parameters are kept.
export function useOpenRecord(param: string): { openId: string | null; open(id: string): void; close(): void } {
  const [searchParams, setSearchParams] = useSearchParams();

  const update = (id: string | null) => {
    setSearchParams(
      (current) => {
        const params = new URLSearchParams(current);
        if (id === null) params.delete(param);
        else params.set(param, id);
        return params;
      },
      { replace: true },
    );
  };

  return {
    openId: searchParams.get(param),
    open: (id) => update(id),
    close: () => update(null),
  };
}
