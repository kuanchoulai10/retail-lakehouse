import type { QueryClient } from "@tanstack/react-query";
import { getGetEffectivePoliciesQueryKey, getGetTableEffectivePoliciesQueryKey } from "./generated/tables/tables";

const [BY_LOCATION_URL] = getGetEffectivePoliciesQueryKey();
const BY_TABLE_URL = getGetTableEffectivePoliciesQueryKey("\u0000")[0];
const [BY_TABLE_START, BY_TABLE_END] = BY_TABLE_URL.split("\u0000") as [string, string];

function isByTableKey(key: unknown): boolean {
  return typeof key === "string" && key.startsWith(BY_TABLE_START) && key.endsWith(BY_TABLE_END);
}

// After any attach or detach, of either kind: what applies anywhere, asked by location or by a
// table's uuid, since one attachment changes it for every target below it.
export async function invalidateEffectivePolicies(queryClient: QueryClient): Promise<void> {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: [BY_LOCATION_URL] }),
    queryClient.invalidateQueries({ predicate: (query) => isByTableKey(query.queryKey[0]) }),
  ]);
}
