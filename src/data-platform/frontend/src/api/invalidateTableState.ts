import type { QueryClient } from "@tanstack/react-query";
import { getGetTableHealthQueryKey, getGetTableQueryKey } from "./generated/tables/tables";

// After a write to a maintained table: its record (status, settings) and its health.
export function invalidateTableState(queryClient: QueryClient, tableUuid: string): Promise<void[]> {
  return Promise.all(
    [getGetTableQueryKey(tableUuid), getGetTableHealthQueryKey(tableUuid)].map((queryKey) =>
      queryClient.invalidateQueries({ queryKey }),
    ),
  );
}
