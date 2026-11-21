import { Banner, Skeleton } from "@retail-lakehouse/design-system";
import { useMutation, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { invalidateDiscoveryPolicyAttachments } from "@/api/invalidateDiscoveryPolicyAttachments";
import { invalidatePolicyAttachments } from "@/api/invalidatePolicyAttachments";
import {
  attachTableDiscoveryPolicy,
  useListTableDiscoveryPolicies,
} from "@/api/generated/discovery-policies/discovery-policies";
import {
  attachTableMaintenancePolicy,
  useListTableMaintenancePolicies,
} from "@/api/generated/maintenance-policies/maintenance-policies";
import type { PolicyTargetApiRequest } from "@/api/generated/model";
import { scopePath, type PolicyScope } from "@/lib/policyScope";
import { FormDialog } from "@/components/forms/FormDialog";
import { SelectField } from "@/components/forms/SelectField";
import { errorMessage } from "@/format";

export type PolicyKind = "maintenance" | "discovery";

interface Props {
  kind: PolicyKind;
  scope: PolicyScope;
  // The policy of this kind attached to this target now, which the chosen one replaces; null when none is.
  current: string | null;
  onClose: () => void;
}

// Each kind's route to attach through and what an attach of it changes.
const KINDS: Record<
  PolicyKind,
  {
    attach: (name: string, target: PolicyTargetApiRequest) => Promise<unknown>;
    invalidate: (queryClient: QueryClient, name: string, current: string | null) => Promise<unknown>;
  }
> = {
  maintenance: {
    attach: (name, target) => attachTableMaintenancePolicy(name, { target }),
    invalidate: (queryClient, name, current) =>
      invalidatePolicyAttachments(queryClient, current === null ? [name] : [name, current]),
  },
  discovery: {
    attach: (name, target) => attachTableDiscoveryPolicy(name, { target }),
    invalidate: (queryClient) => invalidateDiscoveryPolicyAttachments(queryClient),
  },
};

// The policy names of one kind; both lists are read, the one not shown stays idle.
function usePolicyNames(kind: PolicyKind) {
  const maintenance = useListTableMaintenancePolicies({ query: { enabled: kind === "maintenance" } });
  const discovery = useListTableDiscoveryPolicies({ query: { enabled: kind === "discovery" } });
  const list = kind === "maintenance" ? maintenance : discovery;
  return { ...list, names: list.data?.policies.map((policy) => policy.name) ?? [] };
}

// Attaches a policy of one kind to the page's catalog, namespace or table. A target holds one
// policy of each kind, so attaching where one is attached replaces it.
export function AttachPolicyDialog({ kind, scope, current, onClose }: Props) {
  const queryClient = useQueryClient();
  const policies = usePolicyNames(kind);
  const [chosen, setChosen] = useState<string | undefined>(undefined);
  const [invalid, setInvalid] = useState<string | null>(null);
  const path = scopePath(scope);

  const attach = useMutation({
    mutationFn: (name: string) => KINDS[kind].attach(name, { type: scope.type, path }),
    onSuccess: onClose,
    onSettled: (_result, _error, name) => KINDS[kind].invalidate(queryClient, name, current),
  });

  function submit() {
    if (chosen === undefined) {
      setInvalid("Choose a policy to attach.");
      return;
    }
    setInvalid(null);
    attach.mutate(chosen);
  }

  const options = policies.names
    .filter((name) => name !== current)
    .map((name) => ({ value: name, label: name }))
    .sort((a, b) => a.label.localeCompare(b.label));

  let field;
  if (policies.isPending) {
    field = (
      <>
        <Skeleton className="h-9 w-full" />
        <span className="sr-only">Loading {kind} policies</span>
      </>
    );
  } else if (policies.isError) {
    field = <Banner type="negative" title={`Could not load ${kind} policies: ${errorMessage(policies.error)}`} />;
  } else if (options.length === 0) {
    field = <p className="type-body-medium text-on-surface-variant">There is no other {kind} policy to attach.</p>;
  } else {
    field = <SelectField label="Policy" value={chosen} options={options} placeholder="Choose a policy" onChange={setChosen} />;
  }

  return (
    <FormDialog
      title={current === null ? "Attach policy" : "Replace policy"}
      description={
        <>
          {current === null ? `Attaches a ${kind} policy to` : <>Replaces <span className="font-mono">{current}</span> on</>} the{" "}
          {scope.type} <span className="font-mono break-all">{path.join(".")}</span>.
          {scope.type !== "table" && ` It applies to every table below that has no ${kind} policy attached nearer to it.`}
        </>
      }
      submitLabel="Attach"
      isPending={attach.isPending}
      error={invalid ?? (attach.isError ? errorMessage(attach.error) : null)}
      onSubmit={submit}
      onClose={onClose}
    >
      {field}
    </FormDialog>
  );
}
