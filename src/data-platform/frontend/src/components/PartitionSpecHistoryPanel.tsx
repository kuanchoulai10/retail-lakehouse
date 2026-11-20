import type { CatalogTableApiResponse } from "@/api/generated/model";
import {
  useGetCatalogTablePartitionSpecComparison,
  useListCatalogTablePartitionSpecVersions,
} from "@/api/generated/tables/tables";
import { useSchemaHistorySelection } from "@/components/tabs/useSchemaHistorySelection";
import { VersionHistoryPanel, type VersionHistory } from "@/components/VersionHistoryPanel";
import { apiNamespace } from "@/lib/catalogPaths";
import { partitionChangeSummary } from "@/lib/partitionChangeText";
import { partitionDiffItems } from "@/lib/partitionDiffItems";

function usePartitionSpecComparison(table: CatalogTableApiResponse, specId: number, baseId: number | undefined) {
  return useGetCatalogTablePartitionSpecComparison(
    table.catalog,
    apiNamespace(table.namespace),
    table.name,
    specId,
    baseId === undefined ? {} : { base: baseId },
  );
}

// Every partition spec version of the table, the default one marked, and the comparison of the chosen
// one with the version before it (or any other version).
export function PartitionSpecHistoryPanel({ table }: { table: CatalogTableApiResponse }) {
  const selection = useSchemaHistorySelection();
  const versions = useListCatalogTablePartitionSpecVersions(table.catalog, apiNamespace(table.namespace), table.name);
  const history: VersionHistory | undefined = versions.data && {
    defaultId: versions.data.default_spec_id,
    versions: versions.data.versions.map((version) => ({
      id: version.spec_id,
      previousId: version.previous_spec_id,
      summary: partitionChangeSummary(version.changes),
      ...(version.default ? { badge: "Default" } : {}),
    })),
  };
  return (
    <VersionHistoryPanel
      table={table}
      title="Partition spec"
      noun="partition spec"
      defaultName="default spec"
      history={{ data: history, isError: versions.isError, error: versions.error }}
      chosenId={selection.specId}
      chosenBaseId={selection.baseSpecId}
      onlyChanges={selection.specOnlyChanges}
      onChoose={selection.setSpec}
      onChooseBase={selection.setBaseSpec}
      onOnlyChangesChange={selection.setSpecOnlyChanges}
      useComparison={usePartitionSpecComparison}
      toItems={partitionDiffItems}
      emptyState="Unpartitioned."
    />
  );
}
