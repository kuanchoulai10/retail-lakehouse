import type { ConnectionForm } from "./connectionForm";
import { SelectField } from "./SelectField";
import { TextField } from "./TextField";

// REST is our API's name for a catalog that speaks the Iceberg REST protocol (Ruling R6).
const CONNECTION_OPTIONS = [
  { value: "REST", label: "Iceberg REST" },
  { value: "HADOOP", label: "Hadoop" },
  { value: "HIVE", label: "Hive" },
] as const;

const AUTHENTICATION_OPTIONS = [
  { value: "OAUTH", label: "OAuth" },
  { value: "BEARER", label: "Bearer token" },
  { value: "SIGV4", label: "SigV4" },
  { value: "IMPLICIT", label: "Implicit" },
] as const;

interface Props {
  form: ConnectionForm;
  onChange: (form: ConnectionForm) => void;
}

export function ConnectionConfigFields({ form, onChange }: Props) {
  function set<Key extends keyof ConnectionForm>(key: Key, value: ConnectionForm[Key]) {
    onChange({ ...form, [key]: value });
  }
  return (
    <fieldset className="m-0 flex min-w-0 flex-col gap-3 border-0 p-0">
      <legend className="mb-3 text-sm font-medium">External connection</legend>
      <SelectField
        label="Connection type"
        placeholder="Select connection type"
        value={form.connectionType}
        options={[...CONNECTION_OPTIONS]}
        onChange={(value) => set("connectionType", value)}
      />
      <TextField label="URI" mono placeholder="Optional" value={form.uri} onChange={(v) => set("uri", v)} />
      <SelectField
        label="Authentication"
        placeholder="Select authentication"
        value={form.authenticationType}
        options={[...AUTHENTICATION_OPTIONS]}
        onChange={(value) => set("authenticationType", value)}
      />
      {form.authenticationType === "OAUTH" && (
        <>
          <TextField label="Token URI" mono value={form.tokenUri} onChange={(v) => set("tokenUri", v)} />
          <TextField label="Client ID" value={form.clientId} onChange={(v) => set("clientId", v)} />
          <TextField
            label="Client secret"
            type="password"
            value={form.clientSecret}
            onChange={(v) => set("clientSecret", v)}
          />
          <TextField
            label="Scopes (comma-separated)"
            value={form.scopes}
            onChange={(v) => set("scopes", v)}
          />
        </>
      )}
      {form.authenticationType === "BEARER" && (
        <TextField
          label="Bearer token"
          type="password"
          value={form.bearerToken}
          onChange={(v) => set("bearerToken", v)}
        />
      )}
      {form.authenticationType === "SIGV4" && (
        <>
          <TextField label="SigV4 role ARN" mono value={form.roleArn} onChange={(v) => set("roleArn", v)} />
          <TextField
            label="Role session name"
            value={form.roleSessionName}
            onChange={(v) => set("roleSessionName", v)}
          />
          <TextField label="SigV4 external ID" value={form.externalId} onChange={(v) => set("externalId", v)} />
          <TextField label="Signing region" value={form.signingRegion} onChange={(v) => set("signingRegion", v)} />
          <TextField label="Signing name" value={form.signingName} onChange={(v) => set("signingName", v)} />
        </>
      )}
    </fieldset>
  );
}
