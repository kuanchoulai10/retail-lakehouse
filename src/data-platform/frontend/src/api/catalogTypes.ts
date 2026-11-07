// Mirrors of the catalog API response and request DTOs (JSON names, snake_case kept).
// Snapshot ids are decimal strings. View sql is named `sql` in JSON.

export type CatalogKind = "INTERNAL" | "EXTERNAL";
export type StorageType = "S3" | "AZURE" | "GCS" | "FILE";
export type ConnectionType = "REST" | "HADOOP" | "HIVE";
export type AuthenticationType = "OAUTH" | "BEARER" | "SIGV4" | "IMPLICIT";

export interface StorageConfigApiRequest {
  storage_type: StorageType;
  allowed_locations?: string[];
  region?: string | null;
  role_arn?: string | null;
  external_id?: string | null;
  endpoint?: string | null;
  endpoint_internal?: string | null;
  sts_endpoint?: string | null;
  sts_unavailable?: boolean | null;
  path_style_access?: boolean | null;
  tenant_id?: string | null;
  multi_tenant_app_name?: string | null;
  consent_url?: string | null;
  gcs_service_account?: string | null;
}

export interface AuthenticationParametersApiRequest {
  authentication_type?: AuthenticationType | null;
  token_uri?: string | null;
  client_id?: string | null;
  client_secret?: string | null;
  scopes?: string[] | null;
  bearer_token?: string | null;
  role_arn?: string | null;
  role_session_name?: string | null;
  external_id?: string | null;
  signing_region?: string | null;
  signing_name?: string | null;
}

export interface ConnectionConfigApiRequest {
  connection_type?: ConnectionType | null;
  uri?: string | null;
  authentication?: AuthenticationParametersApiRequest | null;
}

export interface CreateCatalogApiRequest {
  name: string;
  type: CatalogKind;
  default_base_location: string;
  storage_config: StorageConfigApiRequest;
  connection_config?: ConnectionConfigApiRequest | null;
}

export interface UpdateCatalogApiRequest {
  entity_version: number;
  default_base_location: string;
  properties: Record<string, string>;
  storage_config: StorageConfigApiRequest;
}

export interface StorageConfigApiResponse {
  storage_type: string;
  allowed_locations: string[];
  region: string | null;
  role_arn: string | null;
  external_id: string | null;
  user_arn: string | null;
  endpoint: string | null;
  endpoint_internal: string | null;
  sts_endpoint: string | null;
  sts_unavailable: boolean | null;
  path_style_access: boolean | null;
  tenant_id: string | null;
  multi_tenant_app_name: string | null;
  consent_url: string | null;
  gcs_service_account: string | null;
}

export interface AuthenticationParametersApiResponse {
  authentication_type: string;
  token_uri: string | null;
  client_id: string | null;
  scopes: string[];
  role_arn: string | null;
  role_session_name: string | null;
  external_id: string | null;
  signing_region: string | null;
  signing_name: string | null;
}

export interface ConnectionConfigApiResponse {
  connection_type: string;
  uri: string | null;
  authentication: AuthenticationParametersApiResponse | null;
}

export interface CatalogApiResponse {
  name: string;
  type: string;
  default_base_location: string | null;
  properties: Record<string, string>;
  storage_config: StorageConfigApiResponse;
  connection_config: ConnectionConfigApiResponse | null;
  entity_version: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface CreateNamespaceApiRequest {
  namespace: string[];
  properties?: Record<string, string>;
}

export interface UpdateNamespacePropertiesApiRequest {
  updates?: Record<string, string>;
  removals?: string[];
}

export interface NamespaceApiResponse {
  catalog: string;
  namespace: string[];
  properties: Record<string, string>;
}

export interface NamespaceSummaryApiResponse {
  catalog: string;
  namespace: string[];
}

export interface SchemaFieldApiRequest {
  name: string;
  type: string;
  required?: boolean;
  doc?: string | null;
}

export interface PartitionFieldApiRequest {
  source_column: string;
  transform: string;
}

export interface CreateTableApiRequest {
  name: string;
  schema_fields: SchemaFieldApiRequest[];
  partition_fields?: PartitionFieldApiRequest[];
  location?: string | null;
  properties?: Record<string, string>;
}

export interface RenameTableApiRequest {
  target_namespace: string[];
  target_name: string;
}

export interface UpdateTablePropertiesApiRequest {
  expected_uuid: string;
  updates?: Record<string, string>;
  removals?: string[];
}

export interface SchemaFieldApiResponse {
  id: number;
  name: string;
  type: string;
  required: boolean;
  doc: string | null;
}

export interface SchemaApiResponse {
  schema_id: number;
  fields: SchemaFieldApiResponse[];
}

export interface PartitionFieldApiResponse {
  source_id: number;
  field_id: number;
  name: string;
  transform: string;
}

export interface PartitionSpecApiResponse {
  spec_id: number;
  fields: PartitionFieldApiResponse[];
}

export interface SortFieldApiResponse {
  source_id: number;
  transform: string;
  direction: string;
  null_order: string;
}

export interface SortOrderApiResponse {
  order_id: number;
  fields: SortFieldApiResponse[];
}

export interface SnapshotApiResponse {
  id: string;
  parent_id: string | null;
  timestamp_ms: number;
  operation: string | null;
  summary: Record<string, string>;
}

export interface TableSummaryApiResponse {
  total_records: number | null;
  total_data_files: number | null;
  total_files_size: number | null;
}

export interface CatalogTableApiResponse {
  catalog: string;
  namespace: string[];
  name: string;
  uuid: string;
  format_version: number;
  location: string;
  current_snapshot_id: string | null;
  last_updated_ms: number;
  schema: SchemaApiResponse;
  partition_spec: PartitionSpecApiResponse;
  sort_order: SortOrderApiResponse;
  snapshots: SnapshotApiResponse[];
  properties: Record<string, string>;
  summary: TableSummaryApiResponse;
}

export interface TableIdentifierApiResponse {
  catalog: string;
  namespace: string[];
  name: string;
}

export interface CreateViewApiRequest {
  name: string;
  sql: string;
  dialect: string;
}

export interface ViewVersionApiResponse {
  version_id: number;
  timestamp_ms: number;
  sql: string;
}

export interface ViewApiResponse {
  catalog: string;
  namespace: string[];
  name: string;
  uuid: string;
  location: string;
  sql: string;
  dialect: string;
  default_namespace: string[];
  current_version_id: number;
  schema: SchemaApiResponse;
  versions: ViewVersionApiResponse[];
  properties: Record<string, string>;
}

export type ViewIdentifierApiResponse = TableIdentifierApiResponse;

export interface CreateGenericTableApiRequest {
  name: string;
  format: string;
  base_location?: string | null;
  doc?: string | null;
  properties?: Record<string, string>;
}

export interface GenericTableApiResponse {
  catalog: string;
  namespace: string[];
  name: string;
  format: string;
  base_location: string | null;
  doc: string | null;
  properties: Record<string, string>;
}

export type GenericTableIdentifierApiResponse = TableIdentifierApiResponse;

export interface CoveredCatalogsApiResponse {
  catalogs: string[];
}
