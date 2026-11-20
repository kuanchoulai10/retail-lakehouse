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
import { policyChecksText } from "@/lib/policyChecksText";
import type { PolicyContent } from "@/lib/policyDraft";

// The server always seeds the default policy and flags it with `is_default` (its name is only
// for display); a new policy copies it, so without it there is nothing to start from, and the
// console never guesses the values.
const NO_DEFAULT_MESSAGE =
  "The default policy is missing, so a new policy has nothing to start from. Reload the page.";

type Policy = ListedTableMaintenancePolicyApiResponse;

function contentOf(policy: Policy): PolicyContent {
  return {
    description: policy.description,
    on: policy.on,
    dry_run: policy.dry_run,
    rewrite_data_files: policy.rewrite_data_files,
    rewrite_manifests: policy.rewrite_manifests,
    expire_snapshots: policy.expire_snapshots,
    remove_orphan_files: policy.remove_orphan_files,
  };
}

function deleteDisabledReason(policy: Policy): string | null {
  if (policy.is_default) return "The default policy cannot be deleted.";
  if (policy.attachment_count > 0) return "Detach it from every target before deleting it.";
  return null;
}

// The default first, then by name.
function inListOrder(policies: Policy[]): Policy[] {
  return [...policies].sort(
    (a, b) => Number(b.is_default) - Number(a.is_default) || a.name.localeCompare(b.name),
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
  const defaultPolicy = rows.find((policy) => policy.is_default);
  return (
    <>
      <ResourceListPage
        title="Maintenance policies"
        columns={[
          {
            header: "Name",
            cell: (row) => (
              <span className="flex flex-wrap items-center gap-2">
                <span className="font-mono font-medium">{row.name}</span>
                {row.is_default && <Badge>Default</Badge>}
              </span>
            ),
          },
          {
            header: "Description",
            cell: (row) =>
              row.description === "" ? <span className="text-on-surface-variant">—</span> : row.description,
          },
          { header: "Checks", cell: (row) => policyChecksText(row.on) },
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
        newDisabled={defaultPolicy === undefined}
        errors={defaultPolicy === undefined ? [NO_DEFAULT_MESSAGE] : []}
        renderForm={({ onClose }) =>
          defaultPolicy !== undefined && (
            <PolicyEditor content={{ ...contentOf(defaultPolicy), description: "" }} onClose={onClose} />
          )
        }
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
      {editing !== null && (
        <PolicyEditor policy={editing} content={contentOf(editing)} onClose={() => setEditing(null)} />
      )}
    </>
  );
}
