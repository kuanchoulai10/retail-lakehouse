import { Badge, Banner, Button, Panel, Skeleton, TextLink } from "@retail-lakehouse/design-system";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import {
  detachTableMaintenancePolicy,
  getGetApplicableMaintenancePolicyQueryOptions,
  getGetTableApplicableMaintenancePolicyQueryOptions,
} from "@/api/generated/maintenance-policies/maintenance-policies";
import type { ApplicableTableMaintenancePolicyApiResponse, PolicyTargetApiResponse } from "@/api/generated/model";
import { AttachPolicyDialog } from "@/components/AttachPolicyDialog";
import { errorMessage } from "@/format";
import { invalidatePolicyAttachments } from "@/api/invalidatePolicyAttachments";
import { policyVersionPath, targetKind, targetName, targetPagePath } from "@/lib/policyPaths";
import { scopePath, type PolicyScope } from "@/lib/policyScope";

export type { PolicyScope } from "@/lib/policyScope";

// A table attachment is keyed by the table's uuid, so it stays the table's across a rename.
function attachedHere(scope: PolicyScope, target: PolicyTargetApiResponse | null): boolean {
  if (target === null || target.type !== scope.type) return false;
  if (scope.type === "table") return target.table_uuid === scope.tableUuid;
  const path = scopePath(scope);
  return target.path.length === path.length && target.path.every((part, index) => part === path[index]);
}

// A table maintenance has a record of is asked by uuid, the name it plans under; any other
// target is asked by name, the namespace dot-joined as the API takes it. Either answer counts a
// table attachment, since the API finds an unrecorded table's uuid in the catalog.
function applicableQuery(scope: PolicyScope) {
  if (scope.type === "table" && scope.recorded) return getGetTableApplicableMaintenancePolicyQueryOptions(scope.tableUuid);
  if (scope.type === "catalog") return getGetApplicableMaintenancePolicyQueryOptions({ catalog: scope.catalog });
  const namespace = scope.namespace.join(".");
  return getGetApplicableMaintenancePolicyQueryOptions(
    scope.type === "table" ? { catalog: scope.catalog, namespace, table: scope.table } : { catalog: scope.catalog, namespace },
  );
}

function Origin({ scope, policy }: { scope: PolicyScope; policy: ApplicableTableMaintenancePolicyApiResponse }) {
  const target = policy.target;
  if (target === null) {
    return (
      <p>
        <span className="text-on-surface">Platform default</span>
        <span className="text-on-surface-variant">: no policy is attached here or above.</span>
      </p>
    );
  }
  if (attachedHere(scope, target)) return <p>Attached here</p>;
  const href = targetPagePath(target);
  return (
    <p>
      Inherited from {targetKind(target)}{" "}
      {href === null ? (
        <span className="font-mono break-all">{targetName(target)}</span>
      ) : (
        <TextLink asChild inline className="font-mono break-all">
          <Link to={href}>{targetName(target)}</Link>
        </TextLink>
      )}
    </p>
  );
}

// The policy that applies to a catalog, namespace or table, where it comes from, and the
// attach, replace and detach actions for this target. Attaching here overrides what is inherited.
export function ApplicablePolicyPanel({ scope }: { scope: PolicyScope }) {
  const queryClient = useQueryClient();
  const [attaching, setAttaching] = useState(false);
  const applicable = useQuery(applicableQuery(scope));
  const detach = useMutation({
    mutationFn: (name: string) =>
      detachTableMaintenancePolicy(name, {
        target: {
          type: scope.type,
          path: scopePath(scope),
          ...(scope.type === "table" ? { table_uuid: scope.tableUuid } : {}),
        },
      }),
    onSettled: (_result, _error, name) => invalidatePolicyAttachments(queryClient, [name]),
  });

  let body;
  if (applicable.isPending) {
    body = (
      <>
        <Skeleton className="h-4 w-48" />
        <span className="sr-only">Loading the policy that applies</span>
      </>
    );
  } else if (applicable.isError) {
    body = <Banner type="negative" title={`Could not load the policy that applies: ${errorMessage(applicable.error)}`} />;
  } else {
    const policy = applicable.data;
    const here = attachedHere(scope, policy.target);
    body = (
      <div className="type-body-medium flex flex-col gap-3">
        <p className="flex flex-wrap items-center gap-2">
          <TextLink asChild className="font-mono">
            <Link to={policyVersionPath(policy.name, policy.version)}>
              {policy.name} v{policy.version}
            </Link>
          </TextLink>
          {policy.dry_run && <Badge>Dry run</Badge>}
        </p>
        <Origin scope={scope} policy={policy} />
        {detach.isError && <Banner type="negative" title={`Could not detach ${policy.name}: ${errorMessage(detach.error)}`} />}
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            styleType="outlined"
            size="small"
            onClick={() => {
              detach.reset();
              setAttaching(true);
            }}
          >
            {here ? "Replace policy" : "Attach policy"}
          </Button>
          {here && (
            <Button
              type="button"
              styleType="ghost"
              size="small"
              disabled={detach.isPending}
              onClick={() => detach.mutate(policy.name)}
            >
              Detach
            </Button>
          )}
        </div>
        {attaching && (
          <AttachPolicyDialog
            scope={scope}
            current={here ? policy.name : null}
            onClose={() => setAttaching(false)}
          />
        )}
      </div>
    );
  }
  return <Panel title="Maintenance policy">{body}</Panel>;
}
