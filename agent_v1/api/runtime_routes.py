from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

from agent_v1.runtime.docker_manager import docker_manager, DockerError
from agent_v1.runtime.executer import command_executor, ExecutionError
from agent_v1.runtime.registry import runtime_registry, RuntimeNotFound
from agent_v1.api.project_utils import resolve_project_dir


router = APIRouter(prefix="/projects", tags=["runtime"])

# Request / Response Models
class StartRuntimeResponse(BaseModel):
    project_name: str
    status: str
    container_id: str
    image: str


class ExecCommandRequest(BaseModel):
    command: str = Field(..., example="npm")
    args: List[str] = Field(default_factory=list, example=["run", "dev"])
    cwd: Optional[str] = Field(default=".")
    timeout: Optional[int] = Field(default=60)


class ExecCommandResponse(BaseModel):
    return_code: int
    stdout: str
    stderr: str


class RuntimeStatusResponse(BaseModel):
    project_name: str
    status: str
    container_id: Optional[str]
    image: str
    last_command: Optional[str]

# Routes
@router.post(
    "/{project_name}/runtime/start",
    response_model=StartRuntimeResponse
)
def start_runtime(project_name: str):
    """
    Creates and starts a runtime container for the project.
    """
    try:
        # Validate project exists
        project_dir = resolve_project_dir(project_name)

        # Create container (if not exists)
        if not runtime_registry.exists(project_name):
            runtime = docker_manager.create_container(
                project_name=project_name,
                image=None,
            )
        else:
            runtime = runtime_registry.get(project_name)

        # Start container
        runtime = docker_manager.start_container(project_name)

        return StartRuntimeResponse(
            project_name=project_name,
            status=runtime.status,
            container_id=runtime.container_id,
            image=runtime.image,
        )

    except (DockerError, RuntimeNotFound, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{project_name}/runtime/exec",
    response_model=ExecCommandResponse
)
def exec_command(project_name: str, req: ExecCommandRequest):
    """
    Executes a validated command inside the project runtime.
    """
    try:
        code, stdout, stderr = command_executor.exec(
            project_name=project_name,
            command=req.command,
            args=req.args,
            cwd=req.cwd,
            timeout=req.timeout,
        )

        return ExecCommandResponse(
            return_code=code,
            stdout=stdout,
            stderr=stderr,
        )

    except ExecutionError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{project_name}/runtime/stop"
)
def stop_runtime(project_name: str):
    """
    Stops the project's runtime container.
    """
    try:
        docker_manager.stop_container(project_name)
        return {"status": "stopped"}

    except (DockerError, RuntimeNotFound) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/{project_name}/runtime"
)
def remove_runtime(project_name: str):
    """
    Removes the runtime container and clears registry entry.
    """
    try:
        docker_manager.remove_container(project_name)
        return {"status": "removed"}

    except (DockerError, RuntimeNotFound) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/{project_name}/runtime/status",
    response_model=RuntimeStatusResponse
)
def runtime_status(project_name: str):
    """
    Returns runtime status for the project.
    """
    try:
        runtime = runtime_registry.get(project_name)

        return RuntimeStatusResponse(
            project_name=project_name,
            status=runtime.status,
            container_id=runtime.container_id,
            image=runtime.image,
            last_command=runtime.last_command,
        )

    except RuntimeNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
