"""
Purpose:
--------
User-wide project & runtime management API.

Capabilities:
-------------
- List ALL projects owned by logged-in user
- Get runtime status of any project
- Start / stop any container
- Delete any container
- Delete project completely (disk + runtime + container)

Security:
---------
- JWT protected
- User-scoped queries
- NO per-project ownership checks needed
"""

import shutil
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from agent_v1.api.auth.dependencies import AuthDependency
from agent_v1.api.auth.rate_limits import runtime_operation_limit
from agent_v1.api.db.models import Project

from agent_v1.runtime.repository import RuntimeRepository, RuntimeNotFound
from agent_v1.runtime.docker_manager import docker_manager, DockerError
from agent_v1.runtime.terminal_manager import terminal_manager
from agent_v1.api.project_utils import GENERATED_PROJECTS_ROOT

router = APIRouter(
    prefix="/manage",
    tags=["management"],
)

repo = RuntimeRepository()

# -------------------------------------------------------------------
# Response Models
# -------------------------------------------------------------------

class ProjectRuntimeInfo(BaseModel):
    project_name: str
    runtime_status: Optional[str]
    container_id: Optional[str]
    image: Optional[str]

# -------------------------------------------------------------------
# LIST ALL PROJECTS (USER SCOPE)
# -------------------------------------------------------------------

@router.get(
    "/projects",
    response_model=List[ProjectRuntimeInfo],
)
async def list_all_projects(
    user=Depends(AuthDependency.get_current_user),
):
    """
    Returns ALL projects owned by the logged-in user
    with runtime information if exists.
    """
    projects = (
        await Project
        .filter(owner=user)
        .prefetch_related("runtime")
        .all()
    )

    results: list[ProjectRuntimeInfo] = []

    for project in projects:
        runtime = getattr(project, "runtime", None)

        results.append(
            ProjectRuntimeInfo(
                project_name=project.name,
                runtime_status=runtime.status if runtime else None,
                container_id=runtime.container_name if runtime else None,
                image=runtime.image if runtime else None,
            )
        )

    return results

# -------------------------------------------------------------------
# RUNTIME ACTIONS (USER GLOBAL)
# -------------------------------------------------------------------

@router.post(
    "/projects/{project_name}/runtime/start",
    dependencies=[Depends(runtime_operation_limit)],
)
async def start_runtime(
    project_name: str,
    user=Depends(AuthDependency.get_current_user),
):
    project = await Project.get_or_none(name=project_name, owner=user)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        try:
            await repo.get(project.name)
        except RuntimeNotFound:
            await docker_manager.create_container(project.name)

        await docker_manager.start_container(project.name)
        return {"status": "running"}

    except DockerError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/projects/{project_name}/runtime/stop",
    dependencies=[Depends(runtime_operation_limit)],
)
async def stop_runtime(
    project_name: str,
    user=Depends(AuthDependency.get_current_user),
):
    project = await Project.get_or_none(name=project_name, owner=user)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        await docker_manager.stop_container(project.name)
        terminal_manager.close(project.name)
        return {"status": "stopped"}
    except RuntimeNotFound:
        raise HTTPException(status_code=404, detail="Runtime not found")


@router.delete(
    "/projects/{project_name}/runtime",
    dependencies=[Depends(runtime_operation_limit)],
)
async def delete_runtime(
    project_name: str,
    user=Depends(AuthDependency.get_current_user),
):
    project = await Project.get_or_none(name=project_name, owner=user)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        terminal_manager.close(project.name)
        await docker_manager.remove_container(project.name)
        return {"status": "runtime_deleted"}
    except RuntimeNotFound:
        raise HTTPException(status_code=404, detail="Runtime not found")
    except DockerError as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------------
# DELETE PROJECT (USER GLOBAL)
# -------------------------------------------------------------------

@router.delete(
    "/projects/{project_name}",
    dependencies=[Depends(runtime_operation_limit)],
)
async def delete_project(
    project_name: str,
    user=Depends(AuthDependency.get_current_user),
):
    """
    Deletes ENTIRE project owned by user:
    - Stop runtime (if exists)
    - Remove container
    - Delete runtime DB row
    - Delete project DB row
    - Delete project files
    """
    project = await Project.get_or_none(name=project_name, owner=user)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        terminal_manager.close(project.name)
        await docker_manager.remove_container(project.name)
    except RuntimeNotFound:
        pass
    except DockerError as e:
        raise HTTPException(status_code=500, detail=str(e))

    project_path = GENERATED_PROJECTS_ROOT / project.name
    if project_path.exists():
        shutil.rmtree(project_path)

    await project.delete()

    return {
        "status": "project_deleted",
        "project": project.name,
    }
