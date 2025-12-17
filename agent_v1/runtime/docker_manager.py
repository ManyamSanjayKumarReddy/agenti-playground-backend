import subprocess
from typing import Optional, Dict

from agent_v1.runtime.registry import (
    runtime_registry,
    ProjectRuntime,
    RuntimeAlreadyExists,
)
from agent_v1.api.project_utils import resolve_project_dir


class DockerError(Exception):
    pass


class DockerManager:
    """
    Manages Docker container lifecycle per project.
    No command execution here – lifecycle only.
    """

    DEFAULT_IMAGE = "python:3.11-slim"
    WORKDIR = "/workspace"

    def _run(self, args: list[str]) -> str:
        """
        Executes a docker CLI command safely (no shell).
        """
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

    def container_exists(self, name: str) -> bool:
        output = self._run(
            ["ps", "-a", "--filter", f"name=^{name}$", "--format", "{{.Names}}"]
        )
        return output == name

    def is_running(self, name: str) -> bool:
        output = self._run(
            ["ps", "--filter", f"name=^{name}$", "--format", "{{.Names}}"]
        )
        return output == name

    def create_container(
        self,
        project_name: str,
        image: Optional[str] = None,
        ports: Optional[Dict[int, int]] = None,
    ) -> ProjectRuntime:
        """
        Creates (but does not start) a container for a project.
        """
        project_dir = resolve_project_dir(project_name)
        image = image or self.DEFAULT_IMAGE
        container_name = f"ai_builder_{project_name}"

        if runtime_registry.exists(project_name):
            raise RuntimeAlreadyExists(
                f"Runtime already registered for project: {project_name}"
            )

        # Build docker run args
        run_args = [
            "create",
            "--name",
            container_name,
            "-w",
            self.WORKDIR,
            "-v",
            f"{project_dir}:{self.WORKDIR}",
        ]

        if ports:
            for host_port, container_port in ports.items():
                run_args.extend(["-p", f"{host_port}:{container_port}"])

        run_args.append(image)
        run_args.append("sleep")
        run_args.append("infinity")

        self._run(run_args)

        runtime = runtime_registry.create(
            project_name=project_name,
            project_root=str(project_dir),
            image=image,
        )
        runtime.container_id = container_name

        return runtime

    def start_container(self, project_name: str) -> ProjectRuntime:
        runtime = runtime_registry.get(project_name)

        if not runtime.container_id:
            raise DockerError("Container not created")

        if self.is_running(runtime.container_id):
            return runtime

        self._run(["start", runtime.container_id])
        runtime.mark_running(runtime.container_id)
        return runtime

    def stop_container(self, project_name: str):
        runtime = runtime_registry.get(project_name)

        if not runtime.container_id:
            raise DockerError("Container not created")

        if self.is_running(runtime.container_id):
            self._run(["stop", runtime.container_id])
            runtime.mark_stopped()

    def remove_container(self, project_name: str):
        runtime = runtime_registry.get(project_name)

        if runtime.container_id and self.container_exists(runtime.container_id):
            if self.is_running(runtime.container_id):
                self._run(["stop", runtime.container_id])

            self._run(["rm", runtime.container_id])

        runtime_registry.remove(project_name)


# Singleton
docker_manager = DockerManager()
