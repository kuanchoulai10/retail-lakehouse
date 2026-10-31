import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { ApiError, apiGet } from "../api/client";
import type { TableApiResponse, TableMetadataApiResponse } from "../api/types";
import { TableHeader } from "../components/TableHeader";
import { CommitsTab } from "../components/tabs/CommitsTab";
import { MaintenanceTab } from "../components/tabs/MaintenanceTab";
import { OverviewTab } from "../components/tabs/OverviewTab";
import { PropertiesTab } from "../components/tabs/PropertiesTab";
import { SettingsTab } from "../components/tabs/SettingsTab";
import { errorMessage } from "../format";

const TABS = [
  { key: "overview", label: "Overview" },
  { key: "commits", label: "Commits" },
  { key: "maintenance", label: "Maintenance" },
  { key: "properties", label: "Properties" },
  { key: "settings", label: "Settings" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

function tabOf(segment: string | undefined): TabKey {
  return TABS.find((t) => t.key === segment)?.key ?? "overview";
}

function isNotInCatalog(error: unknown): error is ApiError {
  return (
    error instanceof ApiError && error.status === 404 && error.detail.endsWith("is not in the catalog")
  );
}

export function TablePage() {
  const { uuid = "", tab: segment } = useParams();
  const tab = tabOf(segment);
  const table = useQuery({
    queryKey: ["table", uuid],
    queryFn: () => apiGet<TableApiResponse>(`/v1/tables/${uuid}`),
  });
  const metadata = useQuery({
    queryKey: ["metadata", uuid],
    queryFn: () => apiGet<TableMetadataApiResponse>(`/v1/tables/${uuid}/metadata`),
  });

  if (table.isPending) return <p>Loading table…</p>;
  if (table.isError) {
    return (
      <p role="alert" className="error">
        Could not load table: {errorMessage(table.error)}
      </p>
    );
  }

  const needsCatalog = tab === "overview" || tab === "commits" || tab === "properties";

  function body() {
    if (needsCatalog && isNotInCatalog(metadata.error)) {
      return (
        <p role="status" className="notice">
          {metadata.error.detail}
        </p>
      );
    }
    if (needsCatalog && metadata.isError) {
      return (
        <p role="alert" className="error">
          Could not load table metadata: {errorMessage(metadata.error)}
        </p>
      );
    }
    switch (tab) {
      case "commits":
        return <CommitsTab tableUuid={uuid} />;
      case "maintenance":
        return <MaintenanceTab tableUuid={uuid} />;
      case "properties":
        return metadata.data ? <PropertiesTab metadata={metadata.data} /> : <p>Loading…</p>;
      case "overview":
        return metadata.data ? (
          <OverviewTab tableUuid={uuid} metadata={metadata.data} />
        ) : (
          <p>Loading…</p>
        );
      case "settings":
        return <SettingsTab tableUuid={uuid} />;
      default:
        return null;
    }
  }

  return (
    <section>
      <TableHeader table={table.data} metadata={metadata.data} />
      <nav className="tabs" aria-label="Table sections">
        {TABS.map((t) => (
          <Link
            key={t.key}
            to={`/tables/${uuid}/${t.key}`}
            aria-current={t.key === tab ? "page" : undefined}
          >
            {t.label}
          </Link>
        ))}
      </nav>
      {body()}
    </section>
  );
}
