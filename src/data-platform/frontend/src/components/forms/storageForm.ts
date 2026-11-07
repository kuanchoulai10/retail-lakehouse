import type {
  StorageConfigApiRequest,
  StorageConfigApiResponse,
  StorageType,
} from "@/api/catalogTypes";

export const STORAGE_TYPES: StorageType[] = ["S3", "AZURE", "GCS", "FILE"];

// The storage fields of the catalog forms, as the inputs hold them. A boolean stays null
// until the user sets it, so an untouched checkbox sends nothing.
export interface StorageForm {
  storageType: StorageType;
  allowedLocations: string;
  region: string;
  roleArn: string;
  externalId: string;
  endpoint: string;
  endpointInternal: string;
  stsEndpoint: string;
  stsUnavailable: boolean | null;
  pathStyleAccess: boolean | null;
  tenantId: string;
  multiTenantAppName: string;
  consentUrl: string;
  gcsServiceAccount: string;
}

export function emptyStorageForm(): StorageForm {
  return {
    storageType: "S3",
    allowedLocations: "",
    region: "",
    roleArn: "",
    externalId: "",
    endpoint: "",
    endpointInternal: "",
    stsEndpoint: "",
    stsUnavailable: null,
    pathStyleAccess: null,
    tenantId: "",
    multiTenantAppName: "",
    consentUrl: "",
    gcsServiceAccount: "",
  };
}

function isStorageType(value: string): value is StorageType {
  return (STORAGE_TYPES as string[]).includes(value);
}

export function storageFormFrom(config: StorageConfigApiResponse): StorageForm {
  return {
    storageType: isStorageType(config.storage_type) ? config.storage_type : "S3",
    allowedLocations: config.allowed_locations.join(", "),
    region: config.region ?? "",
    roleArn: config.role_arn ?? "",
    externalId: config.external_id ?? "",
    endpoint: config.endpoint ?? "",
    endpointInternal: config.endpoint_internal ?? "",
    stsEndpoint: config.sts_endpoint ?? "",
    stsUnavailable: config.sts_unavailable,
    pathStyleAccess: config.path_style_access,
    tenantId: config.tenant_id ?? "",
    multiTenantAppName: config.multi_tenant_app_name ?? "",
    consentUrl: config.consent_url ?? "",
    gcsServiceAccount: config.gcs_service_account ?? "",
  };
}

export function splitList(text: string): string[] {
  return text
    .split(",")
    .map((part) => part.trim())
    .filter((part) => part !== "");
}

type TextKey = Exclude<
  keyof StorageConfigApiRequest,
  "storage_type" | "allowed_locations" | "sts_unavailable" | "path_style_access"
>;

function setText(request: StorageConfigApiRequest, key: TextKey, text: string) {
  const value = text.trim();
  if (value !== "") request[key] = value;
}

// Sends only the fields of the chosen storage type that the user filled in (Ruling R7).
export function storageConfigRequest(form: StorageForm): StorageConfigApiRequest {
  const request: StorageConfigApiRequest = { storage_type: form.storageType };
  const allowed = splitList(form.allowedLocations);
  if (allowed.length > 0) request.allowed_locations = allowed;
  if (form.storageType === "S3") {
    setText(request, "region", form.region);
    setText(request, "role_arn", form.roleArn);
    setText(request, "external_id", form.externalId);
    setText(request, "endpoint", form.endpoint);
    setText(request, "endpoint_internal", form.endpointInternal);
    setText(request, "sts_endpoint", form.stsEndpoint);
    if (form.stsUnavailable !== null) request.sts_unavailable = form.stsUnavailable;
    if (form.pathStyleAccess !== null) request.path_style_access = form.pathStyleAccess;
  }
  if (form.storageType === "AZURE") {
    setText(request, "tenant_id", form.tenantId);
    setText(request, "multi_tenant_app_name", form.multiTenantAppName);
    setText(request, "consent_url", form.consentUrl);
  }
  if (form.storageType === "GCS") {
    setText(request, "gcs_service_account", form.gcsServiceAccount);
  }
  return request;
}

export function storageFormError(form: StorageForm): string | null {
  if (form.storageType === "AZURE" && form.tenantId.trim() === "") {
    return "Tenant ID is required for Azure";
  }
  return null;
}
