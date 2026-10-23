"""Define the IsoDatetimeCodec for datetimes stored inside JSON."""

from __future__ import annotations

from datetime import UTC, datetime


class IsoDatetimeCodec:
    """Convert timezone-aware datetimes to and from ISO-8601 UTC strings."""

    @staticmethod
    def encode(value: datetime | None) -> str | None:
        """Return the UTC ISO-8601 string, or None."""
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime is not allowed; use timezone-aware UTC")
        return value.astimezone(UTC).isoformat()

    @staticmethod
    def decode(value: str | None) -> datetime | None:
        """Return the timezone-aware UTC datetime, or None."""
        if value is None:
            return None
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
