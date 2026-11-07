import { CheckboxField } from "./CheckboxField";
import { SelectField } from "./SelectField";
import type { StorageForm } from "./storageForm";
import { TextField } from "./TextField";

const STORAGE_OPTIONS = [
  { value: "S3", label: "S3" },
  { value: "AZURE", label: "Azure" },
  { value: "GCS", label: "GCS" },
  { value: "FILE", label: "File" },
] as const;

interface Props {
  form: StorageForm;
  onChange: (form: StorageForm) => void;
}

export function StorageConfigFields({ form, onChange }: Props) {
  function set<Key extends keyof StorageForm>(key: Key, value: StorageForm[Key]) {
    onChange({ ...form, [key]: value });
  }
  return (
    <fieldset className="m-0 flex min-w-0 flex-col gap-3 border-0 p-0">
      <legend className="mb-3 text-sm font-medium">Storage</legend>
      <SelectField
        label="Storage type"
        value={form.storageType}
        options={[...STORAGE_OPTIONS]}
        onChange={(value) => set("storageType", value)}
      />
      <TextField
        label="Allowed locations (comma-separated)"
        mono
        placeholder="s3://bucket1/, s3://bucket2/"
        value={form.allowedLocations}
        onChange={(value) => set("allowedLocations", value)}
      />
      {form.storageType === "S3" && (
        <>
          <TextField label="Region" value={form.region} onChange={(v) => set("region", v)} />
          <TextField label="Role ARN" mono value={form.roleArn} onChange={(v) => set("roleArn", v)} />
          <TextField label="External ID" value={form.externalId} onChange={(v) => set("externalId", v)} />
          <TextField label="Endpoint" mono value={form.endpoint} onChange={(v) => set("endpoint", v)} />
          <TextField
            label="Internal endpoint"
            mono
            value={form.endpointInternal}
            onChange={(v) => set("endpointInternal", v)}
          />
          <TextField label="STS endpoint" mono value={form.stsEndpoint} onChange={(v) => set("stsEndpoint", v)} />
          <CheckboxField
            label="STS unavailable"
            checked={form.stsUnavailable === true}
            onChange={(v) => set("stsUnavailable", v)}
          />
          <CheckboxField
            label="Path style access"
            checked={form.pathStyleAccess === true}
            onChange={(v) => set("pathStyleAccess", v)}
          />
        </>
      )}
      {form.storageType === "AZURE" && (
        <>
          <TextField label="Tenant ID" value={form.tenantId} onChange={(v) => set("tenantId", v)} />
          <TextField
            label="Multi-tenant app name"
            value={form.multiTenantAppName}
            onChange={(v) => set("multiTenantAppName", v)}
          />
          <TextField label="Consent URL" mono value={form.consentUrl} onChange={(v) => set("consentUrl", v)} />
        </>
      )}
      {form.storageType === "GCS" && (
        <TextField
          label="Service account"
          value={form.gcsServiceAccount}
          onChange={(v) => set("gcsServiceAccount", v)}
        />
      )}
    </fieldset>
  );
}
