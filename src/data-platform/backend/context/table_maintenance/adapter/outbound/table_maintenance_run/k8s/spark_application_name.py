"""Define the spark_application_name function."""

from __future__ import annotations

from shared_kernel import prefixed_id_pattern

_CODES: dict[str, str] = {
    "rewrite_data_files": "rdf",
    "rewrite_manifests": "rm",
    "expire_snapshots": "es",
    "remove_orphan_files": "rof",
}
_RUN_ID_PREFIX = "mr"
_RUN_ID = prefixed_id_pattern(_RUN_ID_PREFIX)


def spark_application_name(run_id: str, operation: str, attempt: int) -> str:
    """Build a deterministic DNS-1123 label naming one Spark application attempt.

    The name is ``tm-<operation code>-<suffix>-a<attempt>``, the suffix being the 26 characters after the run
    id's ``mr-`` prefix (docs/adr/0011), so two runs minted in the same millisecond still get different names.
    """
    if attempt < 1:
        msg = f"attempt must be >= 1, got {attempt}"
        raise ValueError(msg)
    if operation not in _CODES:
        msg = f"unknown maintenance operation {operation!r}"
        raise ValueError(msg)
    if not _RUN_ID.fullmatch(run_id):
        msg = f"run id must look like {_RUN_ID_PREFIX}-<26 base32 characters>, got {run_id!r}"
        raise ValueError(msg)
    return f"tm-{_CODES[operation]}-{run_id.removeprefix(f'{_RUN_ID_PREFIX}-')}-a{attempt}"
