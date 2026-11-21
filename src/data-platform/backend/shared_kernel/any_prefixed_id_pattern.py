"""The regular expression an id of any prefix matches."""

from __future__ import annotations

import re

from shared_kernel._id_suffix import ID_SUFFIX
from shared_kernel._prefix_pattern import PREFIX_PATTERN


def any_prefixed_id_pattern() -> re.Pattern[str]:
    """Return the pattern ``^[a-z]{2,8}-[0-7][0-9a-hjkmnp-tv-z]{25}$``, which an id of every prefix matches.

    For a rule that refuses whatever is shaped like an id (a name, say), whichever kind it would be.
    """
    return re.compile(rf"^{PREFIX_PATTERN.pattern}-{ID_SUFFIX}$")
