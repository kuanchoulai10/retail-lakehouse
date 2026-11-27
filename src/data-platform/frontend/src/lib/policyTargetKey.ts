import type { PolicyTargetRef } from "@/lib/policyPaths";

// A place holds one policy of each kind, so its type and path tell a policy's places apart. The parts
// are joined by U+001F, which no name holds, so a part containing a dot stays one part.
export function policyTargetKey(target: PolicyTargetRef): string {
  return [target.type, ...target.path].join("\u001f");
}
