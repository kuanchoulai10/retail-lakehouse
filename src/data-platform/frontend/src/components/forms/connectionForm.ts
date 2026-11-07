import type {
  AuthenticationParametersApiRequest,
  AuthenticationType,
  ConnectionConfigApiRequest,
  ConnectionType,
} from "@/api/catalogTypes";
import { splitList } from "./storageForm";

// The connection fields of the create catalog form for an EXTERNAL catalog. The secrets
// (client secret, bearer token) are typed in and sent once; nothing ever fills them back in.
export interface ConnectionForm {
  connectionType: ConnectionType | undefined;
  uri: string;
  authenticationType: AuthenticationType | undefined;
  tokenUri: string;
  clientId: string;
  clientSecret: string;
  scopes: string;
  bearerToken: string;
  roleArn: string;
  roleSessionName: string;
  externalId: string;
  signingRegion: string;
  signingName: string;
}

export function emptyConnectionForm(): ConnectionForm {
  return {
    connectionType: undefined,
    uri: "",
    authenticationType: undefined,
    tokenUri: "",
    clientId: "",
    clientSecret: "",
    scopes: "",
    bearerToken: "",
    roleArn: "",
    roleSessionName: "",
    externalId: "",
    signingRegion: "",
    signingName: "",
  };
}

function text(value: string): string | undefined {
  const trimmed = value.trim();
  return trimmed === "" ? undefined : trimmed;
}

function authentication(form: ConnectionForm): AuthenticationParametersApiRequest | undefined {
  switch (form.authenticationType) {
    case "OAUTH": {
      const scopes = splitList(form.scopes);
      return {
        authentication_type: "OAUTH",
        token_uri: text(form.tokenUri),
        client_id: text(form.clientId),
        client_secret: text(form.clientSecret),
        scopes: scopes.length > 0 ? scopes : undefined,
      };
    }
    case "BEARER":
      return { authentication_type: "BEARER", bearer_token: text(form.bearerToken) };
    case "SIGV4":
      return {
        authentication_type: "SIGV4",
        role_arn: text(form.roleArn),
        role_session_name: text(form.roleSessionName),
        external_id: text(form.externalId),
        signing_region: text(form.signingRegion),
        signing_name: text(form.signingName),
      };
    case "IMPLICIT":
      return { authentication_type: "IMPLICIT" };
    case undefined:
      return undefined;
  }
}

export function connectionConfigRequest(form: ConnectionForm): ConnectionConfigApiRequest {
  return {
    connection_type: form.connectionType,
    uri: text(form.uri),
    authentication: authentication(form),
  };
}

export function connectionFormError(form: ConnectionForm): string | null {
  if (form.connectionType === undefined) return "Connection type is required";
  if (form.authenticationType === undefined) return "Authentication is required";
  return null;
}
