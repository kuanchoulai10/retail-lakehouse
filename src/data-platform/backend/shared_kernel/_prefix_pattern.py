"""The pattern of a prefixed id's prefix."""

from __future__ import annotations

import re

PREFIX_PATTERN = re.compile(r"[a-z]{2,8}")
