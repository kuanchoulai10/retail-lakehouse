from pydantic import BaseModel


class RewriteManifestsConfig(BaseModel):
    table: str | None = None
    use_caching: bool = True
    spec_id: int | None = None
