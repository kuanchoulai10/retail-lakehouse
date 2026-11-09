import { Banner } from "@retail-lakehouse/design-system";
import { useGetTable } from "@/api/generated/tables/tables";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { SettingsForm } from "@/components/SettingsForm";
import { errorMessage } from "@/format";

interface Props {
  tableUuid: string;
}

export function SettingsTab({ tableUuid }: Props) {
  const table = useGetTable(tableUuid);
  if (table.isPending) return <PanelSkeleton label="Loading settings…" />;
  if (table.isError) {
    return <Banner type="negative" title={`Could not load settings: ${errorMessage(table.error)}`} />;
  }
  return <SettingsForm key={table.data.updated_at} table={table.data} />;
}
