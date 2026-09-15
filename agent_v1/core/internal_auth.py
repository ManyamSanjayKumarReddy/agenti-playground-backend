"""
Purpose:
--------
Trust boundary for agentbay as an internal-only service.

Agentbay no longer authenticates end users (JWT/User model removed) —
it is called exclusively by the ZeroTo control plane, which already
authenticated the end user and authorized the request against org
plans/quotas. This mirrors ZeroTo's own node <-> control-plane trust
pattern (`x-internal-secret` header) instead of inventing a new one.
"""

import os
from fastapi import Header, HTTPException, status

INTERNAL_SECRET = os.environ.get("INTERNAL_SECRET", "")


async def require_internal_secret(x_internal_secret: str = Header(default="")):
    if not INTERNAL_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="INTERNAL_SECRET is not configured",
        )

    if x_internal_secret != INTERNAL_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal secret",
        )
