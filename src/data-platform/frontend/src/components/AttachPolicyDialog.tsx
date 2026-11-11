import { Banner, Skeleton } from "@retail-lakehouse/design-system";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { invalidatePolicyAttachments } from "@/api/invalidatePolicyAttachments";
import {
  attachTableMaintenancePolicy,
  useListTableMaintenancePolicies,
} from "@/api/generated/maintenance-policies/maintenance-policies";
import { scopePath, type PolicyScope } from "@/lib/policyScope";
import { FormDialog } from "@/components/forms/FormDialog";
import { SelectField } from "@/components/forms/SelectField";
import { errorMessage } from "@/format";

interface Props {
  scope: PolicyScope;
  // The policy attached to this target now, which the chosen one replaces; null when none is.
  current: string | null;
  onClose: () => void;
}

// Attaches a policy to the page's catalog, namespace or table. A target holds one policy, so
// attaching where one is attached replaces it.
export function AttachPolicyDialog({ scope, current, onClose }: Props) {
  const queryClient = useQueryClient();
  const policies = useListTableMaintenancePolicies();
  const [chosen, setChosen] = useState<string | undefined>(undefined);
  const [invalid, setInvalid] = useState<string | null>(null);
  const path = scopePath(scope);

  const attach = useMutation({
    mutationFn: (name: string) => attachTableMaintenancePolicy(name, { target: { type: scope.type, path } }),
    onSuccess: onClose,
    onSettled: (_result, _error, name) =>
      invalidatePolicyAttachments(queryClient, current === null ? [name] : [name, current]),
  });

  function submit() {
    if (chosen === undefined) {
      setInvalid("Choose a policy to attach.");
      return;
    }
    setInvalid(null);
    attach.mutate(chosen);
  }

  const options = (policies.data?.policies ?? [])
    .filter((policy) => policy.name !== current)
    .map((policy) => ({ value: policy.name, label: policy.name }))
    .sort((a, b) => a.label.localeCompare(b.label));

  let field;
  if (policies.isPending) {
    field = (
      <>
        <Skeleton className="h-9 w-full" />
        <span className="sr-only">Loading policies</span>
      </>
    );
  } else if (policies.isError) {
    field = <Banner type="negative" title={`Could not load policies: ${errorMessage(policies.error)}`} />;
  } else if (options.length === 0) {
    field = <p className="type-body-medium text-on-surface-variant">There is no other policy to attach.</p>;
  } else {
    field = <SelectField label="Policy" value={chosen} options={options} placeholder="Choose a policy" onChange={setChosen} />;
  }

  return (
    <FormDialog
      title={current === null ? "Attach policy" : "Replace policy"}
      description={
        <>
          {current === null ? "Attaches a policy to" : <>Replaces <span className="font-mono">{current}</span> on</>} the{" "}
          {scope.type} <span className="font-mono break-all">{path.join(".")}</span>.
          {scope.type !== "table" && " It applies to every table below that has no policy attached nearer to it."}
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
