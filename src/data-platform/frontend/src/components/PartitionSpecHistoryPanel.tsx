import { Banner, DiffList, Panel, Select } from "@retail-lakehouse/design-system";
import type { CatalogTableApiResponse, CatalogTablePartitionSpecVersionsApiResponse } from "@/api/generated/model";
import {
  useGetCatalogTablePartitionSpecComparison,
  useListCatalogTablePartitionSpecVersions,
} from "@/api/generated/tables/tables";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { useSchemaHistorySelection } from "@/components/tabs/useSchemaHistorySelection";
import { VersionList } from "@/components/VersionList";
import { errorMessage } from "@/format";
import { apiNamespace } from "@/lib/catalogPaths";
import { partitionChangeSummary } from "@/lib/partitionChangeText";
import { partitionDiffItems } from "@/lib/partitionDiffItems";

const PREVIOUS = "previous";

interface Props {
  table: CatalogTableApiResponse;
}

interface ViewProps extends Props {
  history: CatalogTablePartitionSpecVersionsApiResponse;
}

function PartitionSpecHistoryView({ table, history }: ViewProps) {
  const selection = useSchemaHistorySelection();
  const { versions, default_spec_id: defaultId } = history;
  const has = (id: number | undefined): id is number => versions.some((version) => version.spec_id === id);
  const selectedId = has(selection.specId) ? selection.specId : defaultId;
  const selected = versions.find((version) => version.spec_id === selectedId);
  const baseId = has(selection.baseSpecId) && selection.baseSpecId !== selectedId ? selection.baseSpecId : undefined;
  const previousId = selected?.previous_spec_id ?? null;
  const comparison = useGetCatalogTablePartitionSpecComparison(
    table.catalog,
    apiNamespace(table.namespace),
    table.name,
    selectedId,
    baseId === undefined ? {} : { base: baseId },
  );
  const missing = selection.specId !== undefined && !has(selection.specId);

  return (
    <div className="flex flex-col gap-4 md:flex-row">
      <div className="md:w-64 md:shrink-0">
        <VersionList
          label="Partition spec versions"
          versions={versions.map((version) => ({
            id: version.spec_id,
            title: `v${version.spec_id}`,
            description: partitionChangeSummary(version.changes),
            ...(version.default ? { badge: "Default" } : {}),
          }))}
          selectedId={selectedId}
          onSelect={selection.setSpec}
        />
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        {missing ? (
          <p className="type-body-small text-on-surface-variant">
            {`Partition spec v${selection.specId} is not in this table's history; showing the default spec (v${defaultId}).`}
          </p>
        ) : null}
        <Select
          label="Compare with"
          className="md:max-w-xs"
          value={baseId === undefined ? PREVIOUS : String(baseId)}
          onValueChange={(value) => selection.setBaseSpec(value === PREVIOUS ? undefined : Number(value))}
          items={[
            { value: PREVIOUS, label: previousId === null ? "No earlier version" : `Previous version (v${previousId})` },
            ...versions
              .filter((version) => version.spec_id !== selectedId)
              .map((version) => ({ value: String(version.spec_id), label: `v${version.spec_id}` })),
          ]}
        />
        {comparison.isError ? (
          <Banner
            type="negative"
            title={`Could not load the partition spec comparison: ${errorMessage(comparison.error)}`}
          />
        ) : comparison.data === undefined ? (
          <PanelSkeleton label="Loading the partition spec comparison" />
        ) : (
          <DiffList
            caption={`Changes in partition spec v${selectedId}`}
            items={partitionDiffItems(comparison.data)}
            onlyChanges={selection.specOnlyChanges}
            onOnlyChangesChange={selection.setSpecOnlyChanges}
            emptyState="Unpartitioned."
          />
        )}
      </div>
    </div>
  );
}

// Every partition spec version of the table, the default one marked, and the comparison of the chosen
// one with the version before it (or any other version).
export function PartitionSpecHistoryPanel({ table }: Props) {
  const history = useListCatalogTablePartitionSpecVersions(table.catalog, apiNamespace(table.namespace), table.name);
  return (
    <Panel title="Partition spec">
      {history.isError ? (
        <Banner type="negative" title={`Could not load partition spec versions: ${errorMessage(history.error)}`} />
      ) : history.data === undefined ? (
        <PanelSkeleton label="Loading partition spec versions" />
      ) : (
        <PartitionSpecHistoryView table={table} history={history.data} />
      )}
    </Panel>
  );
}
