import type { CatalogTableApiResponse } from "@/api/generated/model";
import { PropertiesPanel } from "@/components/PropertiesPanel";

export function PropertiesTab({ table }: { table: CatalogTableApiResponse }) {
  return <PropertiesPanel properties={table.properties} />;
}
