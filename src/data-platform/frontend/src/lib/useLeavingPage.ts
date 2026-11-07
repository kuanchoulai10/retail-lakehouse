import { useQueryClient, type QueryKey } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

// For a page that deletes (or renames) the object it shows and then navigates away.
//
// React Router applies a navigation inside startTransition, so the old page can render again
// before the new one commits (a mutation's success re-render, for one). If the object's queries
// were removed by then, useQuery would build them anew and refetch the object that is gone.
// So `leave()` first disables the page's queries (pass `enabled: !leaving`), and the queries
// are removed only when the page unmounts, when no observer of them is left.
//
// The page must be keyed by the object it shows, so that leaving always unmounts it and the
// keys captured on the first render are the object's.
export function useLeavingPage(queryKeys: readonly QueryKey[]) {
  const queryClient = useQueryClient();
  const [keys] = useState(queryKeys);
  const [leaving, setLeaving] = useState(false);
  const left = useRef(false);

  useEffect(
    () => () => {
      if (!left.current) return;
      for (const queryKey of keys) queryClient.removeQueries({ queryKey });
    },
    [queryClient, keys],
  );

  const leave = useCallback(() => {
    left.current = true;
    setLeaving(true);
  }, []);

  return { leaving, leave };
}
