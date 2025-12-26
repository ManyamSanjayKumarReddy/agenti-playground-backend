"""
Purpose:
--------
HTTP + WebSocket API for runtime management.

Security:
---------
- JWT protected
- Project ownership enforced
- Runtime actions rate-limited
"""

import asyncio
from typing import Optional

from fastapi import (
    APIRouter,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
    Depends,
)
from pydantic import BaseModel

from agent_v1.api.auth.dependencies import AuthDependency
from agent_v1.api.auth.rate_limits import runtime_operation_limit
from agent_v1.api.guards import ensure_project_access
from agent_v1.core.jwt_manager import JWTManager

from agent_v1.runtime.docker_manager import docker_manager, DockerError
from agent_v1.runtime.repository import RuntimeRepository, RuntimeNotFound
from agent_v1.runtime.terminal_manager import terminal_manager
from agent_v1.api.db.models import User

router = APIRouter(prefix="/projects", tags=["runtime"])
repo = RuntimeRepository()

# -------------------------------------------------------------------
# Response Models
# -------------------------------------------------------------------

class StartRuntimeResponse(BaseModel):
    project_name: str
    status: str
    container_id: str
    image: str


class RuntimeStatusResponse(BaseModel):
    project_name: str
    container_status: str
    container_id: Optional[str]
    image: str


# -------------------------------------------------------------------
# Container Lifecycle
# -------------------------------------------------------------------

@router.post(
    "/{project_name}/runtime/start",
    response_model=StartRuntimeResponse,
    dependencies=[Depends(runtime_operation_limit)],
)
async def start_runtime(
    project_name: str,
    user: AuthDependency.current_user,
):
    project = await ensure_project_access(project_name, user)

    try:
        try:
            await repo.get(project.name)
        except RuntimeNotFound:
            await docker_manager.create_container(project.name)

        await docker_manager.start_container(project.name)
        runtime = await repo.get(project.name)

        return StartRuntimeResponse(
            project_name=runtime.project.name,  # ✅ FIX
            status=runtime.status,
            container_id=runtime.container_name,
            image=runtime.image,
        )

    except DockerError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/{project_name}/runtime/status",
    response_model=RuntimeStatusResponse,
    dependencies=[Depends(runtime_operation_limit)],
)
async def runtime_status(
    project_name: str,
    user: AuthDependency.current_user,
):
    await ensure_project_access(project_name, user)

    try:
        runtime = await repo.get(project_name)
        return RuntimeStatusResponse(
            project_name=runtime.project.name,  # ✅ FIX
            container_status=runtime.status,
            container_id=runtime.container_name,
            image=runtime.image,
        )

    except RuntimeNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Runtime not found",
        )


@router.post(
    "/{project_name}/runtime/stop",
    dependencies=[Depends(runtime_operation_limit)],
)
async def stop_runtime(
    project_name: str,
    user: AuthDependency.current_user,
):
    await ensure_project_access(project_name, user)

    try:
        await docker_manager.stop_container(project_name)
        terminal_manager.close(project_name)
        return {"status": "stopped"}

    except RuntimeNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Runtime not found",
        )


@router.delete(
    "/{project_name}/runtime",
    dependencies=[Depends(runtime_operation_limit)],
)
async def delete_runtime(
    project_name: str,
    user: AuthDependency.current_user,
):
    await ensure_project_access(project_name, user)

    try:
        terminal_manager.close(project_name)
        await docker_manager.remove_container(project_name)
        return {"status": "deleted"}

    except RuntimeNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Runtime not found",
        )

# -------------------------------------------------------------------
# WebSocket Terminal
# -------------------------------------------------------------------

@router.websocket("/{project_name}/runtime/ws/terminal")
async def runtime_terminal_ws(
    websocket: WebSocket,
    project_name: str,
):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = JWTManager.decode_token(token)
        if payload.get("token_type") != "access":
            raise ValueError("Invalid token type")

        user = await User.get_or_none(
            id=payload["sub"],
            is_active=True,
        )
        if not user:
            raise ValueError("Invalid user")

        await ensure_project_access(project_name, user)

        runtime = await repo.get(project_name)
        if runtime.status != "running":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    session = terminal_manager.get_or_create(
        project_name,
        runtime.container_name,
    )

    async def push_output():
        try:
            while True:
                data = session.read()
                if data:
                    await websocket.send_text(data)
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(push_output())

    try:
        while True:
            msg = await websocket.receive_text()
            session.write(msg)
    except WebSocketDisconnect:
        pass
    finally:
        task.cancel()
        terminal_manager.close(project_name)
