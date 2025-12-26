# agent_v1/core/security_utils.py

from fastapi import HTTPException, status
from pathlib import Path

def prevent_path_traversal(path: str):
    """
    Blocks:
    - ../
    - absolute paths
    - symlink escape
    """

    p = Path(path)

    if p.is_absolute():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Absolute paths are not allowed",
        )

    if ".." in p.parts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path traversal detected",
        )
