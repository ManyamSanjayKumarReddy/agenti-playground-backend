import time
from collections import defaultdict
from fastapi import HTTPException, status


class RateLimiter:
    """
    Simple in-memory rate limiter.
    Keyed by (scope + user_id or ip).
    """

    def __init__(self):
        self._store = defaultdict(list)

    def check(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ):
        now = time.time()
        window_start = now - window_seconds

        hits = self._store[key]

        # Remove expired hits
        while hits and hits[0] < window_start:
            hits.pop(0)

        if len(hits) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )

        hits.append(now)


rate_limiter = RateLimiter()
