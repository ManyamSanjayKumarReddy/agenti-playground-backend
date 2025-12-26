# agent_v1/api/auth/rate_limits.py

import time
from collections import defaultdict
from fastapi import Depends, HTTPException, Request, status

from agent_v1.api.auth.dependencies import AuthDependency

# -------------------------------------------------
# Internal storage (user_id -> [timestamps])
# -------------------------------------------------

_project_generation_bucket = defaultdict(list)
_file_ops_bucket = defaultdict(list)
_runtime_ops_bucket = defaultdict(list)

# -------------------------------------------------
# Helpers
# -------------------------------------------------

def _rate_limit(bucket, key: str, limit: int, window: int):
    now = time.time()

    # Remove expired timestamps
    bucket[key] = [t for t in bucket[key] if now - t < window]

    if len(bucket[key]) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please slow down.",
        )

    bucket[key].append(now)


def _get_rate_key(request: Request, user):
    if user:
        return f"user:{user.id}"

    # Fallback for unauthenticated / edge cases
    client = request.client
    ip = client.host if client else "unknown"
    return f"ip:{ip}"

# -------------------------------------------------
# Rate limit dependencies
# -------------------------------------------------

async def project_generation_limit(
    request: Request,
    user=Depends(AuthDependency.get_current_user),
):
    """
    LIMIT:
    - 5 project generations per minute per user
    """
    if user.is_admin:
        return  # admin bypass

    key = _get_rate_key(request, user)
    _rate_limit(
        bucket=_project_generation_bucket,
        key=key,
        limit=5,
        window=60,
    )


async def file_ops_limit(
    request: Request,
    user=Depends(AuthDependency.get_current_user),
):
    """
    LIMIT:
    - 60 file/folder operations per minute per user
    """
    if user.is_admin:
        return  # admin bypass

    key = _get_rate_key(request, user)
    _rate_limit(
        bucket=_file_ops_bucket,
        key=key,
        limit=60,
        window=60,
    )


async def runtime_operation_limit(
    request: Request,
    user=Depends(AuthDependency.get_current_user),
):
    """
    LIMIT:
    - 20 runtime actions per minute per user
    """
    if user.is_admin:
        return  # admin bypass

    key = _get_rate_key(request, user)
    _rate_limit(
        bucket=_runtime_ops_bucket,
        key=key,
        limit=20,
        window=60,
    )
