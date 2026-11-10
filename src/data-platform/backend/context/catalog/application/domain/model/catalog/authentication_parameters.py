"""Define the AuthenticationParameters value object."""

from __future__ import annotations

from pydantic import Field, model_validator

from base import ValueObject
from context.catalog.application.domain.model.catalog.authentication_type import (
    AuthenticationType,
)

_FIELDS_BY_TYPE: dict[AuthenticationType, frozenset[str]] = {
    AuthenticationType.OAUTH: frozenset({"token_uri", "client_id", "client_secret", "scopes"}),
    AuthenticationType.BEARER: frozenset({"bearer_token"}),
    AuthenticationType.SIGV4: frozenset(
        {"role_arn", "role_session_name", "external_id", "signing_region", "signing_name"}
    ),
    AuthenticationType.IMPLICIT: frozenset(),
}


class AuthenticationParameters(ValueObject):
    """How an external catalog's connection authenticates; each field belongs to one type.

    - OAUTH: ``token_uri``, ``client_id``, ``client_secret``, ``scopes``.
    - BEARER: ``bearer_token``.
    - SIGV4: ``role_arn``, ``role_session_name``, ``external_id``, ``signing_region``, ``signing_name``.
    - IMPLICIT: none; the credentials come from the catalog service's environment.

    A field of another type that holds a value is refused. ``client_secret`` and
    ``bearer_token`` are secrets: they are read in when a catalog is created, the catalog
    service never returns them, and neither ``to_primitives`` nor ``repr`` carries them.
    """

    authentication_type: AuthenticationType
    token_uri: str | None = None
    client_id: str | None = None
    client_secret: str | None = Field(default=None, repr=False, exclude=True)
    scopes: tuple[str, ...] = ()
    bearer_token: str | None = Field(default=None, repr=False, exclude=True)
    role_arn: str | None = None
    role_session_name: str | None = None
    external_id: str | None = None
    signing_region: str | None = None
    signing_name: str | None = None

    @model_validator(mode="after")
    def _fields_belong_to_the_type(self) -> AuthenticationParameters:
        allowed = _FIELDS_BY_TYPE[self.authentication_type] | {"authentication_type"}
        misplaced = sorted(
            name for name in type(self).model_fields if name not in allowed and getattr(self, name) not in (None, ())
        )
        if misplaced:
            raise ValueError(f"{', '.join(misplaced)} does not apply to {self.authentication_type} authentication")
        return self
