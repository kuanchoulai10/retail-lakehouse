import { catalogPath, namespacePath, tablePath } from "@/lib/catalogPaths";

// Where a policy is attached or inherited from: the catalog, then the namespace levels, then the
// table name for a table (the shape attachments and reconciliation records carry).
export interface PolicyTargetRef {
  type: string;
  path: string[];
}

const TARGET_KINDS: Record<string, string> = {
  catalog: "catalog",
  namespace: "namespace",
  table: "table",
};

export function policiesPath(): string {
  return "/policies";
}

export function policyVersionPath(name: string, version: number): string {
  return `/policies/${encodeURIComponent(name)}/versions/${version}`;
}

// "catalog", "namespace" or "table", lower case for use inside a sentence.
export function targetKind(target: PolicyTargetRef): string {
  return TARGET_KINDS[target.type] ?? target.type;
}

// The dotted name shown for a target, as the API's messages name it.
export function targetName(target: PolicyTargetRef): string {
  return target.path.join(".");
}

// The page of the catalog, namespace or table a target names, or null when it names none.
export function targetPagePath(target: PolicyTargetRef): string | null {
  const [catalog, ...rest] = target.path;
  if (catalog === undefined) return null;
  if (target.type === "catalog") return catalogPath(catalog);
  if (target.type === "namespace") return namespacePath(catalog, rest);
  const table = rest.at(-1);
  return target.type === "table" && table !== undefined && rest.length > 1 ? tablePath(catalog, rest.slice(0, -1), table) : null;
}
