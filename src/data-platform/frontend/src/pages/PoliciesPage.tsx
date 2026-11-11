import { Badge, Banner, Button } from "@retail-lakehouse/design-system";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  deleteTableMaintenancePolicy,
  getGetTableMaintenancePolicyQueryKey,
  getListTableMaintenancePoliciesQueryKey,
  getListTableMaintenancePolicyMappingsQueryKey,
  useListTableMaintenancePolicies,
} from "@/api/generated/maintenance-policies/maintenance-policies";
import type { ListedTableMaintenancePolicyApiResponse } from "@/api/generated/model";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { PolicyAttachments } from "@/components/PolicyAttachments";
import { PolicyEditor } from "@/components/PolicyEditor";
import { ResourceListPage } from "@/components/ResourceListPage";
import { errorMessage } from "@/format";
import type { PolicyContent } from "@/lib/policyDraft";

const DEFAULT_POLICY = "default";

type Policy = ListedTableMaintenancePolicyApiResponse;

function contentOf(policy: Policy): PolicyContent {
  return {
    description: policy.description,
    reconcile_interval_seconds: policy.reconcile_interval_seconds,
    dry_run: policy.dry_run,
    operations: policy.operations,
  };
}

function deleteDisabledReason(policy: Policy): string | null {
  if (policy.name === DEFAULT_POLICY) return "The default policy cannot be deleted.";
  if (policy.attachment_count > 0) return "Detach it from every target before deleting it.";
  return null;
}

// The default first, then by name.
function inListOrder(policies: Policy[]): Policy[] {
  return [...policies].sort(
    (a, b) => Number(b.name === DEFAULT_POLICY) - Number(a.name === DEFAULT_POLICY) || a.name.localeCompare(b.name),
  );
}

export function PoliciesPage() {
  const queryClient = useQueryClient();
  const policies = useListTableMaintenancePolicies();
  // The policy as it was when Edit was pressed: a refetch while the editor is open must not
  // replace what the user is editing.
  const [editing, setEditing] = useState<Policy | null>(null);
  const remove = useMutation({
    mutationFn: (policy: Policy) => deleteTableMaintenancePolicy(policy.name),
    onSuccess: (_result, policy) => {
      queryClient.removeQueries({ queryKey: getGetTableMaintenancePolicyQueryKey(policy.name) });
      queryClient.removeQueries({ queryKey: getListTableMaintenancePolicyMappingsQueryKey(policy.name) });
    },
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: getListTableMaintenancePoliciesQueryKey(), exact: true });
    },
  });

  if (policies.isPending) return <PanelSkeleton label="Loading policies" />;
  if (policies.isError) {
    return <Banner type="negative" title={`Could not load policies: ${errorMessage(policies.error)}`} />;
  }

  const rows = inListOrder(policies.data.policies);
  const defaultPolicy = rows.find((policy) => policy.name === DEFAULT_POLICY);
  return (
    <>
      <ResourceListPage
        title="Policies"
        listTitle="Maintenance policies"
        columns={[
          {
            header: "Name",
            cell: (row) => (
              <span className="flex flex-wrap items-center gap-2">
                <span className="font-mono font-medium">{row.name}</span>
                {row.name === DEFAULT_POLICY && <Badge>Default</Badge>}
              </span>
            ),
          },
          {
            header: "Description",
            cell: (row) =>
              row.description === "" ? <span className="text-on-surface-variant">—</span> : row.description,
          },
          { header: "Version", cell: (row) => <span className="tabular-nums">{row.version}</span> },
          {
            header: "Attached to",
            cell: (row) => <PolicyAttachments name={row.name} count={row.attachment_count} />,
          },
        ]}
        rows={rows}
        rowKey={(row) => row.name}
        emptyText="No policies."
        newLabel="New policy"
        renderForm={({ onClose }) => (
          <PolicyEditor
            template={defaultPolicy === undefined ? undefined : { ...contentOf(defaultPolicy), description: "" }}
            onClose={onClose}
          />
        )}
        rowActions={(row) => (
          <Button
            type="button"
            styleType="outlined"
            size="small"
            aria-label={`Edit ${row.name}`}
            onClick={() => setEditing(row)}
          >
            Edit
          </Button>
        )}
        objectKind="policy"
        objectName={(row) => row.name}
        fullPath={(row) => row.name}
        deleteDisabledReason={deleteDisabledReason}
        deleteConsequence={(row) => (
          <>
            This deletes the policy <span className="font-mono">{row.name}</span> and every version of it.
            Reconciliation records keep its name and version number. It cannot be undone.
          </>
        )}
        onDelete={async (row) => {
          await remove.mutateAsync(row);
        }}
      />
      {editing !== null && <PolicyEditor policy={editing} onClose={() => setEditing(null)} />}
    </>
  );
}
