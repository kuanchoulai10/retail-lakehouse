from typing import Optional

from pydantic import BaseModel


class RewriteManifestsConfig(BaseModel):
    """
    Config for CALL <catalog>.system.rewrite_manifests(...)

    Env vars (delimiter: __):
      REWRITE_MANIFESTS__TABLE       required
      REWRITE_MANIFESTS__USE_CACHING optional bool, default true
      REWRITE_MANIFESTS__SPEC_ID     optional int, partition spec ID
    """

    table: Optional[str] = None
    use_caching: bool = True
    spec_id: Optional[int] = None

