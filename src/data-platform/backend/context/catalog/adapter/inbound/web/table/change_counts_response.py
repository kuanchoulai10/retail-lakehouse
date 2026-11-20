"""Define the change_counts_response function."""

from __future__ import annotations

from pydantic import BaseModel


def change_counts_response[M: BaseModel](response_type: type[M], counts: dict[str, int] | None) -> M | None:
    """Map a version's change counts to ``response_type``, or None for the first version.

    The counts must name exactly the response's fields: a kind the response lacks would otherwise
    be dropped without a word, so any difference raises TypeError (a server error) naming the kinds.
    """
    if counts is None:
        return None
    fields = set(response_type.model_fields)
    if set(counts) != fields:
        unknown = sorted(set(counts) - fields)
        missing = sorted(fields - set(counts))
        raise TypeError(
            f"{response_type.__name__} cannot carry these change counts: unknown {unknown}, missing {missing}"
        )
    return response_type.model_validate(counts)
