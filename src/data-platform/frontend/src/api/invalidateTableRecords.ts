import type { QueryClient } from "@tanstack/react-query";
import { getGetTableQueryKey, getListTablesQueryKey } from "./generated/tables/tables";

const [TABLES_URL] = getListTablesQueryKey();
const RECORD_URL = getGetTableQueryKey("\u0000")[0];
const [RECORD_START, RECORD_END] = RECORD_URL.split("\u0000") as [string, string];

// A record's url is the uuid after the tables url, with nothing below it (commits, metrics, ...).
function isRecordKey(key: unknown): boolean {
  if (typeof key !== "string" || !key.startsWith(RECORD_START) || !key.endsWith(RECORD_END)) return false;
  const uuid = key.slice(RECORD_START.length, key.length - RECORD_END.length);
  return uuid !== "" && !uuid.includes("/");
}

// After an attach or detach, of either kind: attaching to a table discovery has not seen registers it
// undecided, so its record, read as missing until then, and every table listing are read again.
export async function invalidateTableRecords(queryClient: QueryClient): Promise<void> {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: [TABLES_URL] }),
    queryClient.invalidateQueries({ predicate: (query) => isRecordKey(query.queryKey[0]) }),
  ]);
}
