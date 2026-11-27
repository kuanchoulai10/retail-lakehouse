import { Badge, Banner, Button, Panel, Skeleton, TextLink } from "@retail-lakehouse/design-system";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { detachTableDiscoveryPolicy } from "@/api/generated/discovery-policies/discovery-policies";
import { detachTableMaintenancePolicy } from "@/api/generated/maintenance-policies/maintenance-policies";
import type {
  DiscoveryEffectivePolicyApiResponse,
  MaintenanceEffectivePolicyApiResponse,
} from "@/api/generated/model";
import {
  getGetEffectivePoliciesQueryOptions,
  getGetTableEffectivePoliciesQueryOptions,
} from "@/api/generated/tables/tables";
import { invalidateDiscoveryPolicyAttachments } from "@/api/invalidateDiscoveryPolicyAttachments";
import { invalidatePolicyAttachments } from "@/api/invalidatePolicyAttachments";
import { AttachPolicyDialog, type PolicyKind } from "@/components/AttachPolicyDialog";
import { errorMessage } from "@/format";
import { discoveryPolicyVersionPath } from "@/lib/discoveryPolicyPaths";
import { effectivePolicyOrigin, type EffectivePolicyOrigin } from "@/lib/effectivePolicyOrigin";
import { policyVersionPath, targetPagePath } from "@/lib/policyPaths";
import type { PolicyScope } from "@/lib/policyScope";

type Entry = MaintenanceEffectivePolicyApiResponse | DiscoveryEffectivePolicyApiResponse;

const LABELS: Record<PolicyKind, string> = { maintenance: "Maintenance", discovery: "Discovery" };

// A table maintenance has a record of is asked by uuid, the name it plans under; any other
// target is asked by location, the namespace dot-joined as the API takes it. Either answer counts
// a table attachment, since the API finds an unrecorded table's uuid in the catalog.
function effectiveQuery(scope: PolicyScope) {
  if (scope.type === "table" && scope.recorded) return getGetTableEffectivePoliciesQueryOptions(scope.tableUuid);
  if (scope.type === "catalog") return getGetEffectivePoliciesQueryOptions({ catalog: scope.catalog });
  const namespace = scope.namespace.join(".");
  return getGetEffectivePoliciesQueryOptions(
    scope.type === "table" ? { catalog: scope.catalog, namespace, table: scope.table } : { catalog: scope.catalog, namespace },
  );
}

// The policy an entry names; a discovery entry names none when no discovery policy applies.
interface AppliedPolicy {
  name: string;
  version: number;
}

function appliedPolicy(entry: Entry): AppliedPolicy | null {
  if (entry.policy_name === null || entry.version === null) return null;
  return { name: entry.policy_name, version: entry.version };
}

// Removes the attachment the entry names, by its pa- or da- id; the platform default has none.
function detachEntry(entry: Entry): Promise<void> {
  const policy = appliedPolicy(entry);
  if (entry.attachment_id === null || policy === null) {
    return Promise.reject(new Error("no policy is attached here"));
  }
  return entry.kind === "maintenance"
    ? detachTableMaintenancePolicy(policy.name, entry.attachment_id)
    : detachTableDiscoveryPolicy(policy.name, entry.attachment_id);
}

function versionPath(kind: PolicyKind, policy: AppliedPolicy): string {
  return kind === "maintenance"
    ? policyVersionPath(policy.name, policy.version)
    : discoveryPolicyVersionPath(policy.name, policy.version);
}

function Origin({ origin }: { origin: EffectivePolicyOrigin }) {
  if (origin.level !== "inherited") return <p>{origin.text}</p>;
  const href = targetPagePath(origin.from);
  const name = origin.from.path.join(".");
  return (
    <p>
      {origin.lead}{" "}
      {href === null ? (
        <span className="font-mono break-all">{name}</span>
      ) : (
        <TextLink asChild inline className="font-mono break-all">
          <Link to={href}>{name}</Link>
        </TextLink>
      )}
    </p>
  );
}

interface RowProps {
  scope: PolicyScope;
  entry: Entry;
  detaching: boolean;
  onAttach: () => void;
  onDetach: () => void;
  attachRef: (button: HTMLButtonElement | null) => void;
  detachRef: (button: HTMLButtonElement | null) => void;
}

function EntryRow({ scope, entry, detaching, onAttach, onDetach, attachRef, detachRef }: RowProps) {
  const policy = appliedPolicy(entry);
  const origin = effectivePolicyOrigin(scope, entry);
  const here = policy !== null && origin.level === "here";
  return (
    <li className="flex flex-col gap-1 border-b border-outline py-2 last:border-b-0">
      <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="text-on-surface-variant">{LABELS[entry.kind]}</span>
        {policy === null ? (
          <span>{`No ${entry.kind} policy applies`}</span>
        ) : (
          <TextLink asChild className="font-mono break-all">
            <Link to={versionPath(entry.kind, policy)}>
              {policy.name} v{policy.version}
            </Link>
          </TextLink>
        )}
        {entry.kind === "maintenance" && entry.dry_run && <Badge>Dry run</Badge>}
      </p>
      {policy !== null && <Origin origin={origin} />}
      {/* Each button says its kind to a screen reader; the row label says it on screen. The name starts
          with the visible label ("Attach policy for maintenance"), so voice control finds it (WCAG 2.5.3). */}
      <div className="flex flex-wrap gap-2 pt-1">
        <Button
          ref={attachRef}
          type="button"
          styleType="outlined"
          size="small"
          onClick={onAttach}
        >
          {here ? "Replace" : "Attach"} policy <span className="sr-only">for {entry.kind}</span>
        </Button>
        {here && (
          <Button
            ref={detachRef}
            type="button"
            styleType="ghost"
            size="small"
            disabled={detaching}
            onClick={onDetach}
          >
            Detach <span className="sr-only">{entry.kind} policy</span>
          </Button>
        )}
      </div>
    </li>
  );
}

function remember(buttons: Map<PolicyKind, HTMLButtonElement>, kind: PolicyKind, button: HTMLButtonElement | null) {
  if (button === null) buttons.delete(kind);
  else buttons.set(kind, button);
}

// The policy of each kind that applies to a catalog, namespace or table, the level it comes from,
// and the attach, replace and detach actions for this target. Attaching here overrides what is
// inherited, for that kind only. Detaching removes an attachment, not the policy, so it does not ask.
export function EffectivePoliciesPanel({ scope }: { scope: PolicyScope }) {
  const queryClient = useQueryClient();
  const [attaching, setAttaching] = useState<{ kind: PolicyKind; current: string | null } | null>(null);
  const attachButtons = useRef(new Map<PolicyKind, HTMLButtonElement>());
  const detachButtons = useRef(new Map<PolicyKind, HTMLButtonElement>());
  // The kind whose Detach gets focus back once a refused detach settles and the button is enabled again.
  const refocus = useRef<PolicyKind | null>(null);
  const effective = useQuery(effectiveQuery(scope));

  const detach = useMutation({
    mutationFn: (entry: Entry) => detachEntry(entry),
    // A write can fail after part of it landed, so the panel refetches either way. A detached
    // row's Detach is gone once the answer is read again, so focus moves to that row's Attach;
    // a refused detach keeps it, and focus goes back to it, which the browser drops while disabled.
    onSettled: async (_result, error, entry) => {
      await (entry.kind === "maintenance"
        ? invalidatePolicyAttachments(queryClient, [entry.policy_name])
        : invalidateDiscoveryPolicyAttachments(queryClient));
      if (error === null) attachButtons.current.get(entry.kind)?.focus();
      else refocus.current = entry.kind;
    },
  });

  useEffect(() => {
    if (detach.isPending || refocus.current === null) return;
    detachButtons.current.get(refocus.current)?.focus();
    refocus.current = null;
  }, [detach.isPending]);

  let body;
  if (effective.isPending) {
    body = (
      <>
        <Skeleton className="h-4 w-48" />
        <span className="sr-only">Loading the policies that apply</span>
      </>
    );
  } else if (effective.isError) {
    body = <Banner type="negative" title={`Could not load the policies that apply: ${errorMessage(effective.error)}`} />;
  } else {
    body = (
      <div className="type-body-medium flex flex-col gap-2">
        {detach.isError && (
          <Banner
            type="negative"
            title={`Could not detach ${detach.variables.policy_name}: ${errorMessage(detach.error)}`}
          />
        )}
        <ul className="m-0 flex list-none flex-col p-0">
          {effective.data.policies.map((entry) => (
            <EntryRow
              key={entry.kind}
              scope={scope}
              entry={entry}
              detaching={detach.isPending}
              onAttach={() => {
                detach.reset();
                const here = effectivePolicyOrigin(scope, entry).level === "here";
                setAttaching({ kind: entry.kind, current: here ? entry.policy_name : null });
              }}
              onDetach={() => detach.mutate(entry)}
              attachRef={(button) => remember(attachButtons.current, entry.kind, button)}
              detachRef={(button) => remember(detachButtons.current, entry.kind, button)}
            />
          ))}
        </ul>
        {attaching !== null && (
          <AttachPolicyDialog
            kind={attaching.kind}
            scope={scope}
            current={attaching.current}
            onClose={() => setAttaching(null)}
          />
        )}
      </div>
    );
  }
  return <Panel title="Policies">{body}</Panel>;
}
