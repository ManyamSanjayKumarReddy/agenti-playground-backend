from datetime import datetime
from typing import Dict, Optional
from threading import RLock

from typing_extensions import runtime


class RuntimeNotFound(Exception):
    pass

class RuntimeAlreadyExists(Exception):
    pass

class ProjectRuntime:
    """ In memory representation of projects runtime state"""

    def __init__(
            self,
            project_name : str,
            project_root : str,
            image : str,
            container_id : Optional[str] = None,
            status : str = 'stopped',
            ports : Optional[Dict[str, int]] = None
    ):
        self.project_name = project_name
        self.project_root = project_root
        self.image = image
        self.container_id = container_id
        self.status = status
        self.ports = ports or {}
        self.created_at = datetime.now()
        self.last_updated_at = datetime.now()
        self.last_command: Optional[str] = None

    def mark_running(self, container_id : str):
        self.container_id = container_id
        self.status = "running"
        self.last_updated_at = datetime.now()

    def mark_stopped(self):
        self.status = "stopped"
        self.last_updated_at = datetime.now()

    def record_command(self, command: str):
        self.last_command = command
        self.last_updated_at = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "project_name": self.project_name,
            "project_root": self.project_root,
            "image": self.image,
            "container_id": self.container_id,
            "status": self.status,
            "ports": self.ports,
            "created_at": self.created_at.isoformat(),
            "last_updated_at": self.last_updated_at.isoformat(),
            "last_command": self.last_command,
        }


class RuntimeRegistry:
    """
    Thread-safe in-memory runtime registry.
    """

    def __init__(self):
        self._runtimes: Dict[str, ProjectRuntime] = {}
        self._lock = RLock()

    def create(
            self,
            project_name :str,
            project_root : str,
            image: str
    ) -> ProjectRuntime:

        with self._lock:
            if project_name in self._runtimes:
                raise RuntimeAlreadyExists(
                    f"Runtime already exists for project: {project_name}"
                )

            runtime = ProjectRuntime(
                project_name = project_name,
                project_root= project_root,
                image = image
            )

            self._runtimes[project_name] = runtime
            return runtime

    def get(self, project_name: str) -> ProjectRuntime:
        with self._lock:
            runtime = self._runtimes.get(project_name)
            if not runtime:
                raise RuntimeNotFound(
                    f"No runtime found for project: {project_name}"
                )
            return runtime

    def exists(self, project_name: str) -> bool:
        with self._lock:
            return project_name in self._runtimes

    def remove(self, project_name: str):
        with self._lock:
            if project_name not in self._runtimes:
                raise RuntimeNotFound(
                    f"No runtime found for project: {project_name}"
                )
            del self._runtimes[project_name]

    def list_all(self) -> Dict[str, Dict]:
        with self._lock:
            return {
                name: runtime.to_dict()
                for name, runtime in self._runtimes.items()
            }

# Singleton registry instance
runtime_registry = RuntimeRegistry()


