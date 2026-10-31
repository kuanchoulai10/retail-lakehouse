import { useQuery } from "@tanstack/react-query";
import { apiGet } from "../../api/client";
import type { TableApiResponse } from "../../api/types";
import { errorMessage } from "../../format";
import { SettingsForm } from "../SettingsForm";

interface Props {
  tableUuid: string;
}

export function SettingsTab({ tableUuid }: Props) {
  const table = useQuery({
    queryKey: ["table", tableUuid],
    queryFn: () => apiGet<TableApiResponse>(`/v1/tables/${tableUuid}`),
  });
  if (table.isPending) return <p>Loading settings…</p>;
  if (table.isError) {
    return (
      <p role="alert" className="error">
        Could not load settings: {errorMessage(table.error)}
      </p>
    );
  }
  return <SettingsForm key={table.data.updated_at} table={table.data} />;
}
