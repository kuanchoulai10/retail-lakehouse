"""The regular expression a prefixed id must match."""

from __future__ import annotations

import re

from shared_kernel._checked_prefix import checked_prefix
from shared_kernel._id_suffix import ID_SUFFIX


def prefixed_id_pattern(prefix: str) -> re.Pattern[str]:
    """Return the pattern ``^<prefix>-[0-7][0-9a-hjkmnp-tv-z]{25}$`` for ids of ``prefix``."""
    return re.compile(rf"^{checked_prefix(prefix)}-{ID_SUFFIX}$")
