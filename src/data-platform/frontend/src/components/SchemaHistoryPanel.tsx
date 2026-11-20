import type { CatalogTableApiResponse } from "@/api/generated/model";
import { useGetCatalogTableSchemaComparison, useListCatalogTableSchemaVersions } from "@/api/generated/tables/tables";
import { useSchemaHistorySelection } from "@/components/tabs/useSchemaHistorySelection";
import { VersionHistoryPanel, type VersionHistory } from "@/components/VersionHistoryPanel";
import { apiNamespace } from "@/lib/catalogPaths";
import { schemaChangeSummary } from "@/lib/schemaChangeText";
import { schemaDiffItems } from "@/lib/schemaDiffItems";

function useSchemaComparison(table: CatalogTableApiResponse, schemaId: number, baseId: number | undefined) {
  return useGetCatalogTableSchemaComparison(
    table.catalog,
    apiNamespace(table.namespace),
    table.name,
    schemaId,
    baseId === undefined ? {} : { base: baseId },
  );
}

// Every schema version of the table, each marked with what it changed, and the comparison of the
// chosen one with the version before it (or any other version).
export function SchemaHistoryPanel({ table }: { table: CatalogTableApiResponse }) {
  const selection = useSchemaHistorySelection();
  const versions = useListCatalogTableSchemaVersions(table.catalog, apiNamespace(table.namespace), table.name);
  const history: VersionHistory | undefined = versions.data && {
    defaultId: versions.data.current_schema_id,
    versions: versions.data.versions.map((version) => ({
      id: version.schema_id,
      previousId: version.previous_schema_id,
      summary: schemaChangeSummary(version.changes),
      ...(version.current ? { badge: "Current" } : {}),
    })),
  };
  return (
    <VersionHistoryPanel
      table={table}
      title="Schema"
      noun="schema"
      defaultName="current schema"
      history={{ data: history, isError: versions.isError, error: versions.error }}
      chosenId={selection.schemaId}
      chosenBaseId={selection.baseSchemaId}
      onlyChanges={selection.schemaOnlyChanges}
      onChoose={selection.setSchema}
      onChooseBase={selection.setBaseSchema}
      onOnlyChangesChange={selection.setSchemaOnlyChanges}
      useComparison={useSchemaComparison}
      toItems={schemaDiffItems}
    />
  );
}
