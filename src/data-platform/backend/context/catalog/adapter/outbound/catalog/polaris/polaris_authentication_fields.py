"""Define POLARIS_AUTHENTICATION_FIELDS: the key of each AuthenticationParameters field in Polaris."""

from __future__ import annotations

POLARIS_AUTHENTICATION_FIELDS: dict[str, str] = {
    "token_uri": "tokenUri",
    "client_id": "clientId",
    "client_secret": "clientSecret",
    "scopes": "scopes",
    "bearer_token": "bearerToken",
    "role_arn": "roleArn",
    "role_session_name": "roleSessionName",
    "external_id": "externalId",
    "signing_region": "signingRegion",
    "signing_name": "signingName",
}
