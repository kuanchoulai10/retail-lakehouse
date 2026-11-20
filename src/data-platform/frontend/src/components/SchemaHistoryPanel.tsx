import { Banner, DiffList, Panel, Select } from "@retail-lakehouse/design-system";
import type { CatalogTableApiResponse, CatalogTableSchemaVersionsApiResponse } from "@/api/generated/model";
import { useGetCatalogTableSchemaComparison, useListCatalogTableSchemaVersions } from "@/api/generated/tables/tables";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { useSchemaHistorySelection } from "@/components/tabs/useSchemaHistorySelection";
import { VersionList } from "@/components/VersionList";
import { errorMessage } from "@/format";
import { apiNamespace } from "@/lib/catalogPaths";
import { schemaChangeSummary } from "@/lib/schemaChangeText";
import { schemaDiffItems } from "@/lib/schemaDiffItems";

const PREVIOUS = "previous";

interface Props {
  table: CatalogTableApiResponse;
}

interface ViewProps extends Props {
  history: CatalogTableSchemaVersionsApiResponse;
}

function SchemaHistoryView({ table, history }: ViewProps) {
  const selection = useSchemaHistorySelection();
  const { versions, current_schema_id: currentId } = history;
  const has = (id: number | undefined): id is number => versions.some((version) => version.schema_id === id);
  const selectedId = has(selection.schemaId) ? selection.schemaId : currentId;
  const selected = versions.find((version) => version.schema_id === selectedId);
  const baseId = has(selection.baseSchemaId) && selection.baseSchemaId !== selectedId ? selection.baseSchemaId : undefined;
  const previousId = selected?.previous_schema_id ?? null;
  const comparison = useGetCatalogTableSchemaComparison(
    table.catalog,
    apiNamespace(table.namespace),
    table.name,
    selectedId,
    baseId === undefined ? {} : { base: baseId },
  );
  const missing = selection.schemaId !== undefined && !has(selection.schemaId);

  return (
    <div className="flex flex-col gap-4 md:flex-row">
      <div className="md:w-64 md:shrink-0">
        <VersionList
          label="Schema versions"
          versions={versions.map((version) => ({
            id: version.schema_id,
            title: `v${version.schema_id}`,
            description: schemaChangeSummary(version.changes),
            ...(version.current ? { badge: "Current" } : {}),
          }))}
          selectedId={selectedId}
          onSelect={selection.setSchema}
        />
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        {missing ? (
          <p className="type-body-small text-on-surface-variant">
            {`Schema v${selection.schemaId} is not in this table's history; showing the current schema (v${currentId}).`}
          </p>
        ) : null}
        <Select
          label="Compare with"
          className="md:max-w-xs"
          value={baseId === undefined ? PREVIOUS : String(baseId)}
          onValueChange={(value) => selection.setBaseSchema(value === PREVIOUS ? undefined : Number(value))}
          items={[
            { value: PREVIOUS, label: previousId === null ? "No earlier version" : `Previous version (v${previousId})` },
            ...versions
              .filter((version) => version.schema_id !== selectedId)
              .map((version) => ({ value: String(version.schema_id), label: `v${version.schema_id}` })),
          ]}
        />
        {comparison.isError ? (
          <Banner type="negative" title={`Could not load the schema comparison: ${errorMessage(comparison.error)}`} />
        ) : comparison.data === undefined ? (
          <PanelSkeleton label="Loading the schema comparison" />
        ) : (
          <DiffList
            caption={`Changes in schema v${selectedId}`}
            items={schemaDiffItems(comparison.data)}
            onlyChanges={selection.schemaOnlyChanges}
            onOnlyChangesChange={selection.setSchemaOnlyChanges}
          />
        )}
      </div>
    </div>
  );
}

// Every schema version of the table, each marked with what it changed, and the comparison of the
// chosen one with the version before it (or any other version).
export function SchemaHistoryPanel({ table }: Props) {
  const history = useListCatalogTableSchemaVersions(table.catalog, apiNamespace(table.namespace), table.name);
  return (
    <Panel title="Schema">
      {history.isError ? (
        <Banner type="negative" title={`Could not load schema versions: ${errorMessage(history.error)}`} />
      ) : history.data === undefined ? (
        <PanelSkeleton label="Loading schema versions" />
      ) : (
        <SchemaHistoryView table={table} history={history.data} />
      )}
    </Panel>
  );
}
