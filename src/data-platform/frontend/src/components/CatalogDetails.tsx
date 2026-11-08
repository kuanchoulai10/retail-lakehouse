import { Panel } from "@retail-lakehouse/design-system";
import type { ReactNode } from "react";
import type { CatalogApiResponse } from "@/api/catalogTypes";

interface Entry {
  label: string;
  value: ReactNode;
  mono?: boolean;
}

function Facts({ entries }: { entries: Entry[] }) {
  return (
    <dl className="grid grid-cols-1 gap-x-4 gap-y-1 sm:grid-cols-[12rem_1fr] sm:gap-y-2">
      {entries.map((entry) => (
        <div key={entry.label} className="contents">
          <dt className="text-on-surface-variant">{entry.label}</dt>
          <dd className={entry.mono === true ? "type-code break-all" : undefined}>{entry.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function present(entries: (Entry | null)[]): Entry[] {
  return entries.filter((entry): entry is Entry => entry !== null);
}

function optional(label: string, value: string | boolean | null, mono = true): Entry | null {
  if (value === null || value === "") return null;
  return { label, value: typeof value === "boolean" ? (value ? "Yes" : "No") : value, mono };
}

// The catalog's storage and, for an EXTERNAL catalog, its connection. Secrets are never
// part of the response, so none can show here.
export function CatalogDetails({ catalog }: { catalog: CatalogApiResponse }) {
  const storage = catalog.storage_config;
  const connection = catalog.connection_config;
  return (
    <>
      <Panel title="Storage">
        <Facts
          entries={present([
            { label: "Catalog type", value: catalog.type },
            { label: "Storage type", value: storage.storage_type },
            optional("Default base location", catalog.default_base_location),
            storage.allowed_locations.length > 0
              ? { label: "Allowed locations", value: storage.allowed_locations.join(", "), mono: true }
              : null,
            optional("Region", storage.region, false),
            optional("Role ARN", storage.role_arn),
            optional("External ID", storage.external_id),
            optional("User ARN", storage.user_arn),
            optional("Endpoint", storage.endpoint),
            optional("Internal endpoint", storage.endpoint_internal),
            optional("STS endpoint", storage.sts_endpoint),
            optional("STS unavailable", storage.sts_unavailable, false),
            optional("Path style access", storage.path_style_access, false),
            optional("Tenant ID", storage.tenant_id),
            optional("Multi-tenant app name", storage.multi_tenant_app_name),
            optional("Consent URL", storage.consent_url),
            optional("Service account", storage.gcs_service_account),
            { label: "Entity version", value: <span className="tabular-nums">{catalog.entity_version}</span> },
          ])}
        />
      </Panel>
      {connection !== null && (
        <Panel title="Connection">
          <Facts
            entries={present([
              { label: "Connection type", value: connection.connection_type },
              optional("URI", connection.uri),
              optional("Authentication", connection.authentication?.authentication_type ?? null, false),
              optional("Token URI", connection.authentication?.token_uri ?? null),
              optional("Client ID", connection.authentication?.client_id ?? null),
              connection.authentication !== null && connection.authentication.scopes.length > 0
                ? { label: "Scopes", value: connection.authentication.scopes.join(", "), mono: true }
                : null,
              optional("Role ARN", connection.authentication?.role_arn ?? null),
              optional("Role session name", connection.authentication?.role_session_name ?? null),
              optional("Signing region", connection.authentication?.signing_region ?? null),
              optional("Signing name", connection.authentication?.signing_name ?? null),
            ])}
          />
        </Panel>
      )}
    </>
  );
}
