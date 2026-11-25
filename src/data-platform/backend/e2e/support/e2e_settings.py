"""Provide E2eSettings, which the e2e reads from the pod's environment and the worker's settings file."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True)
class E2eSettings:
    """Say where the platform's services are, which credentials the e2e uses and what the worker was given.

    The e2e checks the platform from outside, so it reads the worker's settings file as written
    rather than through the backend's settings classes: ``worker_maintenance`` holds only the
    maintenance settings the deployment set, and the worker runs the default for the rest.
    """

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
    worker_maintenance: Mapping[str, object]

    @classmethod
    def from_environment(cls, environ: Mapping[str, str]) -> E2eSettings:
        """Read the settings; a missing variable raises KeyError naming it."""
        worker = yaml.safe_load(Path(environ["E2E_WORKER_CONFIG_FILE"]).read_text()) or {}
        return cls(
            api_url=environ["E2E_API_URL"],
            catalog_uri=environ["E2E_CATALOG_URI"],
            management_uri=environ["E2E_MANAGEMENT_URI"],
            scope=environ["E2E_CATALOG_SCOPE"],
            catalog=environ["E2E_CATALOG"],
            polaris_credential=Path(environ["E2E_POLARIS_CREDENTIAL_FILE"]).read_text().strip(),
            s3_endpoint=environ["E2E_S3_ENDPOINT"],
            s3_region=environ["AWS_REGION"],
            s3_access_key_id=environ["AWS_ACCESS_KEY_ID"],
            s3_secret_access_key=environ["AWS_SECRET_ACCESS_KEY"],
            temporal_address=environ["E2E_TEMPORAL_ADDRESS"],
            temporal_namespace=environ["E2E_TEMPORAL_NAMESPACE"],
            worker_maintenance=worker.get("maintenance") or {},
        )
