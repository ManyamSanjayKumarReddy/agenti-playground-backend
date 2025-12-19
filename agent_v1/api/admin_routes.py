"""
Purpose:
--------
Admin-only API for global runtime and project management.

Admin Capabilities:
-------------------
- List ALL runtimes (across projects)
- Get status of any container
- Stop any container
- Delete any container
- Delete project completely (disk + runtime + container)

Security Model:
---------------
- This router is intended to be protected by admin auth middleware.
- No project ownership checks are enforced here.
"""

from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel

import shutil

from agent_v1.runtime.repository import RuntimeRepository, RuntimeNotFound
from agent_v1.runtime.docker_manager import docker_manager, DockerError
from agent_v1.runtime.terminal_manager import terminal_manager
from agent_v1.api.project_utils import GENERATED_PROJECTS_ROOT

router = APIRouter(prefix="/admin", tags=["admin"])
repo = RuntimeRepository()

# -------------------------------------------------------------------
# Response Models
# -------------------------------------------------------------------

class AdminRuntimeInfo(BaseModel):
    project_name: str
    status: str
    container_id: str | None
    image: str


# -------------------------------------------------------------------
# Runtime Management (Admin)
# -------------------------------------------------------------------

@router.get("/runtimes", response_model=List[AdminRuntimeInfo])
async def list_all_runtimes():
    """
    List all runtimes across all projects.
    """
    runtimes = await repo.list_all()

    return [
        AdminRuntimeInfo(
            project_name=r.project_name,
            status=r.status,
            container_id=r.container_name,
            image=r.image,
        )
        for r in runtimes
    ]


@router.post("/runtimes/{project_name}/stop")
async def admin_stop_runtime(project_name: str):
    """
    Stop any container (admin privilege).
    """
    try:
        await docker_manager.stop_container(project_name)
        terminal_manager.close(project_name)
        return {"status": "stopped", "project": project_name}

    except RuntimeNotFound:
        raise HTTPException(
            status_code=404,
            detail=f"No runtime found for project: {project_name}",
        )


@router.delete("/runtimes/{project_name}")
async def admin_delete_runtime(project_name: str):
    """
    Delete a runtime and container (admin privilege).
    """
    try:
        terminal_manager.close(project_name)
        await docker_manager.remove_container(project_name)
        return {"status": "deleted", "project": project_name}

    except RuntimeNotFound:
        raise HTTPException(
            status_code=404,
            detail=f"No runtime found for project: {project_name}",
        )
    except DockerError as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------------
# Project Deletion (Admin)
# -------------------------------------------------------------------

@router.delete("/projects/{project_name}")
async def admin_delete_project(project_name: str):
    """
    Completely delete a project:
    - Stop container (if running)
    - Delete container & runtime
    - Remove project files from disk

    THIS IS DESTRUCTIVE.
    """
    project_path = GENERATED_PROJECTS_ROOT / project_name

    # 1. Stop & remove runtime if exists
    try:
        terminal_manager.close(project_name)
        await docker_manager.remove_container(project_name)
    except RuntimeNotFound:
        pass  # Project may exist without runtime
    except DockerError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 2. Delete project directory
    if project_path.exists():
        shutil.rmtree(project_path)
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Project directory not found: {project_name}",
        )

    return {
        "status": "project_deleted",
        "project": project_name,
    }
