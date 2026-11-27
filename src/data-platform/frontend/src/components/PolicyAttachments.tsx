import { Badge, Skeleton, TextLink } from "@retail-lakehouse/design-system";
import { Link } from "react-router";
import { useListTableMaintenancePolicyAttachments } from "@/api/generated/maintenance-policies/maintenance-policies";
import type { PolicyTargetApiResponse } from "@/api/generated/model";
import { errorMessage } from "@/format";
import { targetPagePath } from "@/lib/policyPaths";
import { policyTargetKey } from "@/lib/policyTargetKey";

const TARGET_TYPES: Record<string, string> = {
  catalog: "Catalog",
  namespace: "Namespace",
  table: "Table",
};

function Target({ target, orphaned }: { target: PolicyTargetApiResponse; orphaned: boolean }) {
  const name = target.path.join(".");
  const href = orphaned ? null : targetPagePath(target);
  return (
    <li className="flex flex-wrap items-center gap-x-2 gap-y-1">
      <span className="text-on-surface-variant">{TARGET_TYPES[target.type] ?? target.type}</span>
      {href === null ? (
        <span className="font-mono break-all">{name}</span>
      ) : (
        <TextLink asChild className="font-mono break-all">
          <Link to={href}>{name}</Link>
        </TextLink>
      )}
      {orphaned && <Badge>No longer in the catalog</Badge>}
    </li>
  );
}

// Where one policy is attached. The list gives only a count, so the targets are read only for
// a policy that has some.
export function PolicyAttachments({ name, count }: { name: string; count: number }) {
  const attachments = useListTableMaintenancePolicyAttachments(name, { query: { enabled: count > 0 } });
  if (count === 0) return <span className="text-on-surface-variant">Not attached</span>;
  if (attachments.isPending) {
    return (
      <>
        <Skeleton className="h-4 w-32" />
        <span className="sr-only">Loading where {name} is attached</span>
      </>
    );
  }
  if (attachments.isError) {
    return <span className="text-negative-text">Could not load attachments: {errorMessage(attachments.error)}</span>;
  }
  return (
    <ul className="m-0 flex list-none flex-col gap-1 p-0">
      {attachments.data.attachments.map((attachment) => (
        <Target key={policyTargetKey(attachment.target)} {...attachment} />
      ))}
    </ul>
  );
}
