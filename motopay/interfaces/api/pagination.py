from __future__ import annotations

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def clamp_limit(limit: int | None) -> int:
    if limit is None or limit < 1:
        return DEFAULT_LIMIT
    return min(limit, MAX_LIMIT)


def clamp_offset(offset: int | None) -> int:
    if offset is None or offset < 0:
        return 0
    return offset
