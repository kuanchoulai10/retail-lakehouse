import type { QueryClient } from "@tanstack/react-query";

export function invalidateTableState(queryClient: QueryClient, tableUuid: string): Promise<void[]> {
  return Promise.all(
    ["table", "health", "metadata"].map((key) =>
      queryClient.invalidateQueries({ queryKey: [key, tableUuid] }),
    ),
  );
}
