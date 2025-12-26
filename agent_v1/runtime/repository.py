"""
Purpose:
--------
Database access layer for container runtime state.

Design Principles:
------------------
- Database is the single source of truth for *container lifecycle*
- Backend tracks ONLY what it controls
- Application processes are NOT tracked here

What this repository manages:
------------------------------
- Container existence
- Container running / stopped status
- Container metadata (image, name, project root)
- Last executed command (optional, informational)

What this repository deliberately DOES NOT manage:
--------------------------------------------------
- Application process state (Flask, FastAPI, Streamlit, etc.)
- Runtime logs
- Terminal activity

Rationale:
----------
Process execution is handled exclusively via WebSocket terminal.
Tracking process state in DB would be inaccurate and misleading.
"""
# agent_v1/runtime/repository.py

from typing import List
from tortoise.exceptions import DoesNotExist

from agent_v1.api.db.models import Project, ProjectRuntime


class RuntimeNotFound(Exception):
    pass


class RuntimeRepository:
    """
    Repository for ProjectRuntime persistence.

    - Uses Project → Runtime FK relationship
    - One runtime per project
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_project(self, project_name: str) -> Project:
        project = await Project.get_or_none(name=project_name)
        if not project:
            raise DoesNotExist(f"Project not found: {project_name}")
        return project

    # ------------------------------------------------------------------
    # Create / Read
    # ------------------------------------------------------------------

    async def create(
        self,
        project_name: str,
        project_root: str,
        image: str,
        container_name: str,
    ) -> ProjectRuntime:
        project = await self._get_project(project_name)

        return await ProjectRuntime.create(
            project=project,
            project_root=project_root,
            image=image,
            container_name=container_name,
            status="stopped",
        )

    async def get(self, project_name: str) -> ProjectRuntime:
        project = await self._get_project(project_name)

        runtime = (
            await ProjectRuntime.get_or_none(project=project)
            .select_related("project")
        )

        if not runtime:
            raise RuntimeNotFound(project_name)

        return runtime

    async def list_all(self) -> List[ProjectRuntime]:
        return await ProjectRuntime.all().select_related("project")

    # ------------------------------------------------------------------
    # Container lifecycle updates
    # ------------------------------------------------------------------

    async def update_status(self, project_name: str, status: str) -> None:
        project = await self._get_project(project_name)

        updated = await ProjectRuntime.filter(project=project).update(
            status=status
        )

        if not updated:
            raise RuntimeNotFound(project_name)

    async def update_last_command(
        self,
        project_name: str,
        command: str,
    ) -> None:
        project = await self._get_project(project_name)

        updated = await ProjectRuntime.filter(project=project).update(
            last_command=command
        )

        if not updated:
            raise RuntimeNotFound(project_name)

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete(self, project_name: str) -> None:
        project = await self._get_project(project_name)

        deleted = await ProjectRuntime.filter(project=project).delete()

        if not deleted:
            raise RuntimeNotFound(project_name)
