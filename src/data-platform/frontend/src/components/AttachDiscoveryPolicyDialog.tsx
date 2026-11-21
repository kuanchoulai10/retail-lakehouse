import { Banner, Skeleton } from "@retail-lakehouse/design-system";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useListCatalogs } from "@/api/generated/catalogs/catalogs";
import { attachTableDiscoveryPolicy } from "@/api/generated/discovery-policies/discovery-policies";
import type { PolicyTargetApiRequest, PolicyTargetApiRequestType } from "@/api/generated/model";
import { invalidateDiscoveryPolicyAttachments } from "@/api/invalidateDiscoveryPolicyAttachments";
import { errorMessage } from "@/format";
import { FormDialog } from "./forms/FormDialog";
import { SelectField, type SelectOption } from "./forms/SelectField";
import { TextField } from "./forms/TextField";

const TYPES: SelectOption<PolicyTargetApiRequestType>[] = [
  { value: "catalog", label: "Catalog" },
  { value: "namespace", label: "Namespace" },
  { value: "table", label: "Table" },
];

const CATALOG_MESSAGE = "Choose a catalog.";
const NAMESPACE_MESSAGE = "Enter the namespace, its levels joined by dots.";
const TABLE_MESSAGE = "Enter the table's name.";

interface Props {
  policyName: string;
  onClose: () => void;
}

interface Fields {
  type: PolicyTargetApiRequestType;
  catalog: string | undefined;
  namespace: string;
  table: string;
}

// The target the fields name, or the message saying what is missing. The namespace is typed with
// its levels joined by dots, as the API's messages name it.
function targetOf({ type, catalog, namespace, table }: Fields): PolicyTargetApiRequest | string {
  if (catalog === undefined) return CATALOG_MESSAGE;
  if (type === "catalog") return { type, path: [catalog] };
  const levels = namespace.trim().split(".").map((level) => level.trim());
  if (levels.some((level) => level === "")) return NAMESPACE_MESSAGE;
  if (type === "namespace") return { type, path: [catalog, ...levels] };
  const name = table.trim();
  if (name === "") return TABLE_MESSAGE;
  return { type, path: [catalog, ...levels, name] };
}

// Attaches the policy to a catalog picked from Polaris's, or to a namespace or table typed in it.
// A target holds one discovery policy, so attaching replaces the one it has; a target that does not
// exist, or a catalog the platform cannot read, is the API's 404 or 403, shown here.
export function AttachDiscoveryPolicyDialog({ policyName, onClose }: Props) {
  const queryClient = useQueryClient();
  const catalogs = useListCatalogs();
  const [fields, setFields] = useState<Fields>({ type: "catalog", catalog: undefined, namespace: "", table: "" });
  const [invalid, setInvalid] = useState<string | null>(null);

  const attach = useMutation({
    mutationFn: (target: PolicyTargetApiRequest) => attachTableDiscoveryPolicy(policyName, { target }),
    onSuccess: onClose,
    // A write can fail after part of it landed, so the page refetches either way.
    onSettled: () => invalidateDiscoveryPolicyAttachments(queryClient),
  });

  function change(next: Partial<Fields>) {
    setFields((current) => ({ ...current, ...next }));
  }

  function submit() {
    const target = targetOf(fields);
    if (typeof target === "string") {
      setInvalid(target);
      return;
    }
    setInvalid(null);
    attach.mutate(target);
  }

  const options = (catalogs.data ?? [])
    .map((catalog) => ({ value: catalog.name, label: catalog.name }))
    .sort((a, b) => a.label.localeCompare(b.label));

  let catalogField;
  if (catalogs.isPending) {
    catalogField = (
      <>
        <Skeleton className="h-9 w-full" />
        <span className="sr-only">Loading catalogs</span>
      </>
    );
  } else if (catalogs.isError) {
    catalogField = <Banner type="negative" title={`Could not load catalogs: ${errorMessage(catalogs.error)}`} />;
  } else if (options.length === 0) {
    catalogField = <p className="type-body-medium text-on-surface-variant">There is no catalog to attach to.</p>;
  } else {
    catalogField = (
      <SelectField
        label="Catalog"
        value={fields.catalog}
        options={options}
        placeholder="Choose a catalog"
        onChange={(catalog) => change({ catalog })}
      />
    );
  }

  return (
    <FormDialog
      title={`Attach ${policyName}`}
      description={
        <>
          Attaches <span className="font-mono">{policyName}</span> to a catalog, namespace or table. It decides every
          table below that has no discovery policy attached nearer to it, and replaces the policy the target has.
        </>
      }
      submitLabel="Attach"
      isPending={attach.isPending}
      error={invalid ?? (attach.isError ? errorMessage(attach.error) : null)}
      onSubmit={submit}
      onClose={onClose}
    >
      <SelectField label="Type" value={fields.type} options={TYPES} onChange={(type) => change({ type })} />
      {catalogField}
      {fields.type !== "catalog" && (
        <TextField
          label="Namespace"
          mono
          hint="Its levels joined by dots, such as sales.eu."
          value={fields.namespace}
          onChange={(namespace) => change({ namespace })}
        />
      )}
      {fields.type === "table" && (
        <TextField label="Table" mono value={fields.table} onChange={(table) => change({ table })} />
      )}
    </FormDialog>
  );
}
