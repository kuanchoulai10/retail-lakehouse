"""Provide E2eSettings, which the e2e reads from the pod's environment."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True)
class E2eSettings:
    """Say where the platform's services are and which credentials the e2e uses."""

    api_url: str
    catalog_uri: str
    management_uri: str
    scope: str
    catalog: str
    polaris_credential: str = field(repr=False)
    s3_endpoint: str
    s3_region: str
    s3_access_key_id: str = field(repr=False)
    s3_secret_access_key: str = field(repr=False)
    temporal_address: str
    temporal_namespace: str

    @classmethod
    def from_environment(cls, environ: Mapping[str, str]) -> E2eSettings:
        """Read the settings; a missing variable raises KeyError naming it."""
        return cls(
            api_url=environ["E2E_API_URL"],
            catalog_uri=environ["GLAC_CATALOG__URI"],
            management_uri=environ["GLAC_CATALOG__MANAGEMENT_URI"],
            scope=environ["GLAC_CATALOG__SCOPE"],
            catalog=environ["E2E_CATALOG"],
            polaris_credential=Path(environ["E2E_POLARIS_CREDENTIAL_FILE"]).read_text().strip(),
            s3_endpoint=environ["GLAC_CATALOG__S3_ENDPOINT"],
            s3_region=environ["GLAC_CATALOG__S3_REGION"],
            s3_access_key_id=environ["AWS_ACCESS_KEY_ID"],
            s3_secret_access_key=environ["AWS_SECRET_ACCESS_KEY"],
            temporal_address=environ["GLAC_TEMPORAL__ADDRESS"],
            temporal_namespace=environ["GLAC_TEMPORAL__NAMESPACE"],
        )
