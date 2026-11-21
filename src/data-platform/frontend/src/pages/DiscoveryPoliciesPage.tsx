import { Badge, Banner, TextLink } from "@retail-lakehouse/design-system";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";
import {
  deleteTableDiscoveryPolicy,
  getGetTableDiscoveryPolicyQueryKey,
  getListTableDiscoveryPoliciesQueryKey,
  getListTableDiscoveryPolicyAttachmentsQueryKey,
  useListScannedCatalogs,
  useListTableDiscoveryPolicies,
} from "@/api/generated/discovery-policies/discovery-policies";
import type { ListedTableDiscoveryPolicyApiResponse, ScannedCatalogApiResponse } from "@/api/generated/model";
import { CreateDiscoveryPolicyDialog } from "@/components/CreateDiscoveryPolicyDialog";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { ResourceListPage } from "@/components/ResourceListPage";
import { errorMessage } from "@/format";
import { discoveryPolicyPath } from "@/lib/discoveryPolicyPaths";

type Policy = ListedTableDiscoveryPolicyApiResponse;

const NO_MATCH_LABELS: Record<Policy["no_match_outcome"], string> = {
  manage: "Manage",
  unmanage: "Do not manage",
};

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

function ScanFailureBanner({ catalog }: { catalog: ScannedCatalogApiResponse }) {
  if (catalog.failure === null) return null;
  const name = <span className="font-mono">{catalog.catalog}</span>;
  return (
    <Banner
      type="negative"
      title={
        catalog.failure.reason === "not_found" ? (
          <>Catalog {name} no longer exists</>
        ) : (
          <>
            Discovery cannot read catalog {name}: {catalog.failure.detail}
          </>
        )
      }
    />
  );
}

// One banner per scanned catalog whose latest scan failed: its tables keep the decisions of
// the last scan that read them until a scan reads the catalog again.
function ScanFailures() {
  const scanned = useListScannedCatalogs();
  if (scanned.isError) {
    return (
      <Banner
        type="negative"
        title={`Could not check which catalogs discovery can read: ${errorMessage(scanned.error)}`}
      />
    );
  }
  const failing = scanned.data?.catalogs.filter((catalog) => catalog.failure !== null) ?? [];
  if (failing.length === 0) return null;
  return (
    <div className="flex flex-col gap-2">
      {failing.map((catalog) => (
        <ScanFailureBanner key={catalog.catalog} catalog={catalog} />
      ))}
    </div>
  );
}

export function DiscoveryPoliciesPage() {
  const queryClient = useQueryClient();
  const policies = useListTableDiscoveryPolicies();
  const remove = useMutation({
    mutationFn: (policy: Policy) => deleteTableDiscoveryPolicy(policy.name),
    onSuccess: (_result, policy) => {
      queryClient.removeQueries({ queryKey: getGetTableDiscoveryPolicyQueryKey(policy.name) });
      queryClient.removeQueries({ queryKey: getListTableDiscoveryPolicyAttachmentsQueryKey(policy.name) });
    },
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: getListTableDiscoveryPoliciesQueryKey(), exact: true });
    },
  });

  if (policies.isPending) return <PanelSkeleton label="Loading discovery policies" />;
  if (policies.isError) {
    return <Banner type="negative" title={`Could not load discovery policies: ${errorMessage(policies.error)}`} />;
  }

  return (
    <ResourceListPage
      title="Discovery policies"
      notices={<ScanFailures />}
      columns={[
        {
          header: "Name",
          cell: (row) => (
            <span className="flex flex-wrap items-center gap-2">
              <TextLink asChild className="font-mono font-medium">
                <Link to={discoveryPolicyPath(row.name)}>{row.name}</Link>
              </TextLink>
              {row.is_default && <Badge>Default</Badge>}
            </span>
          ),
        },
        {
          header: "Description",
          cell: (row) =>
            row.description === "" ? <span className="text-on-surface-variant">—</span> : row.description,
        },
        { header: "When no rule matches", cell: (row) => NO_MATCH_LABELS[row.no_match_outcome] },
        { header: "Rules", cell: (row) => <span className="tabular-nums">{row.rules.length}</span> },
        { header: "Version", cell: (row) => <span className="tabular-nums">{row.version}</span> },
        { header: "Attached to", cell: (row) => <span className="tabular-nums">{row.attachment_count}</span> },
      ]}
      rows={inListOrder(policies.data.policies)}
      rowKey={(row) => row.name}
      emptyText="No discovery policies."
      newLabel="New policy"
      renderForm={({ onClose }) => <CreateDiscoveryPolicyDialog onClose={onClose} />}
      objectKind="discovery policy"
      objectName={(row) => row.name}
      fullPath={(row) => row.name}
      deleteDisabledReason={deleteDisabledReason}
      deleteConsequence={(row) => (
        <>
          This deletes the discovery policy <span className="font-mono">{row.name}</span> and every version of it. It
          cannot be undone.
        </>
      )}
      onDelete={async (row) => {
        await remove.mutateAsync(row);
      }}
    />
  );
}
