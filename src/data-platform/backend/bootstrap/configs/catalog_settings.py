"""Define the CatalogSettings configuration model."""

from __future__ import annotations

from pydantic import BaseModel, Field, SecretStr


class CatalogSettings(BaseModel):
    """Polaris REST catalog access shared by PyIceberg and the Spark jobs.

    Each name in ``names`` is a Polaris catalog, used as the warehouse. The S3 keys
    are optional; when unset, PyArrow falls back to the AWS credential chain.
    """

    uri: str = "http://polaris.lakehouse-catalog.svc.cluster.local:8181/api/catalog"
    credential: SecretStr = SecretStr("")
    scope: str = "PRINCIPAL_ROLE:ALL"
    names: list[str] = Field(default_factory=lambda: ["iceberg"])
    s3_endpoint: str = "http://rustfs.object-storage.svc.cluster.local:9000"
    s3_path_style_access: bool = True
    s3_region: str = "dummy-region"
    s3_access_key_id: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None
