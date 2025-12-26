"""
Purpose:
--------
Manages Docker container lifecycle for each generated project.

Design Philosophy:
------------------
- This module is the SINGLE authority for Docker container lifecycle.
- Backend manages containers, NOT application processes.
- Application execution happens exclusively via WebSocket terminal.

Responsibilities:
-----------------
- Create Docker containers with resource limits
- Start, stop, and remove containers
- Persist container lifecycle state in the database

Explicitly DOES NOT:
--------------------
- Execute application commands
- Manage processes inside containers
- Handle terminals or WebSockets
- Track application runtime state
"""

import subprocess
import asyncio
from typing import Optional

from agent_v1.api.project_utils import resolve_project_dir
from agent_v1.runtime.repository import RuntimeRepository, RuntimeNotFound
from agent_v1.api.db.models import Project


class DockerError(Exception):
    """Raised when a Docker CLI operation fails."""
    pass


class DockerManager:
    """
    Docker container lifecycle manager.

    One container per project.
    Containers stay alive using `sleep infinity`.
    """

    DEFAULT_IMAGE = "python:3.11-slim"
    WORKDIR = "/workspace"

    def __init__(self):
        self.repo = RuntimeRepository()

    # ------------------------------------------------------------------
    # Docker execution helpers
    # ------------------------------------------------------------------

    def _run(self, args: list[str]) -> str:
        try:
            result = subprocess.run(
                ["docker", *args],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise DockerError(e.stderr.strip() or str(e))

    async def _run_async(self, args: list[str]) -> str:
        return await asyncio.to_thread(self._run, args)

    # ------------------------------------------------------------------
    # Docker state inspection
    # ------------------------------------------------------------------

    def container_exists(self, name: str) -> bool:
        return (
            self._run(
                ["ps", "-a", "--filter", f"name=^{name}$", "--format", "{{.Names}}"]
            )
            == name
        )

    def is_running(self, name: str) -> bool:
        return (
            self._run(
                ["ps", "--filter", f"name=^{name}$", "--format", "{{.Names}}"]
            )
            == name
        )

    # ------------------------------------------------------------------
    # Container lifecycle
    # ------------------------------------------------------------------

    async def create_container(
        self,
        project_name: str,
        image: Optional[str] = None,
    ):
        """
        Create a Docker container for a project.

        - Validates project exists in DB
        - Validates project directory exists
        - Persists runtime metadata
        - Creates container in stopped state
        """
        # 1️⃣ Validate project exists (DB is authority)
        project = await Project.get_or_none(name=project_name)
        if not project:
            raise DockerError(f"Project does not exist: {project_name}")

        # 2️⃣ Validate filesystem
        project_dir = resolve_project_dir(project_name)

        image = image or self.DEFAULT_IMAGE
        container_name = f"ai_builder_{project_name}"

        # 3️⃣ Prevent duplicate runtime creation
        try:
            await self.repo.get(project_name)
            raise DockerError("Runtime already exists for this project")
        except RuntimeNotFound:
            pass

        # 4️⃣ Persist runtime metadata FIRST
        await self.repo.create(
            project_name=project_name,
            project_root=str(project_dir),
            image=image,
            container_name=container_name,
        )

        # 5️⃣ Create container (stopped)
        await self._run_async(
            [
                "create",
                "--name", container_name,
                "--memory", "2g",
                "--cpus", "2.0",
                "-w", self.WORKDIR,
                "-v", f"{project_dir}:{self.WORKDIR}",
                image,
                "sleep", "infinity",
            ]
        )

    async def start_container(self, project_name: str):
        """
        Start the Docker container (idempotent).
        """
        runtime = await self.repo.get(project_name)

        if self.is_running(runtime.container_name):
            return

        await self._run_async(["start", runtime.container_name])
        await self.repo.update_status(project_name, "running")

    async def stop_container(self, project_name: str):
        """
        Stop the Docker container.
        """
        runtime = await self.repo.get(project_name)

        if self.is_running(runtime.container_name):
            await self._run_async(["stop", runtime.container_name])
            await self.repo.update_status(project_name, "stopped")

    async def remove_container(self, project_name: str):
        """
        Remove the Docker container and delete runtime metadata.
        """
        runtime = await self.repo.get(project_name)

        if self.container_exists(runtime.container_name):
            if self.is_running(runtime.container_name):
                await self._run_async(["stop", runtime.container_name])

            await self._run_async(["rm", runtime.container_name])

        # Remove DB record last
        await self.repo.delete(project_name)


# Singleton instance used across the application
docker_manager = DockerManager()
