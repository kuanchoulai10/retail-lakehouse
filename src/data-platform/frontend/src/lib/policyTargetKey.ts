import type { PolicyTargetRef } from "@/lib/policyPaths";

// A place holds one policy of each kind, so its type, path and table uuid tell a policy's places
// apart: two table rows can share a path (an old record and a recreated table), never a uuid. The
// parts are joined by U+001F, which no name holds, so a part containing a dot stays one part.
export function policyTargetKey(target: PolicyTargetRef & { table_uuid?: string | null }): string {
  return [target.type, target.table_uuid ?? "", ...target.path].join("\u001f");
}
