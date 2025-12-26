from fastapi import FastAPI, HTTPException, Body, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
import asyncio

from tortoise import Tortoise
from tortoise.exceptions import IntegrityError

from agent_v1.graph.graph import run_agent
from agent_v1.api.schemas.graph import (
    GenerateProjectRequest,
    GenerateProjectResponse,
    ListFilesResponse,
    ReadFileResponse,
    WriteFileRequest,
)

from agent_v1.tools.utils import (
    api_set_project_root,
    api_list_files,
    api_read_file,
    api_write_file,
    api_delete_file,
    api_create_folder,
    api_delete_folder,
)

from agent_v1.api.runtime_routes import router as runtime_router
from agent_v1.api.user_management_routes import router as management_router
from agent_v1.api.auth.routes import router as auth_router

from agent_v1.api.auth.dependencies import AuthDependency
from agent_v1.api.db.models import Project
from agent_v1.api.guards import ensure_project_access

from agent_v1.api.auth.rate_limits import (
    project_generation_limit,
    file_ops_limit,
)

from agent_v1.api.db.config import init_db
from agent_v1.runtime.reconcile import reconcile_runtimes_on_startup
from agent_v1.runtime.terminal_manager import terminal_manager
from agent_v1.core.logging import setup_logging
from agent_v1.core.middleware import request_id_middleware
from agent_v1.runtime.command_policy import CommandRejected
from agent_v1.api.stats_routes import router as stats_router

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------

setup_logging()

# -------------------------------------------------------------------
# Lifespan
# -------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await reconcile_runtimes_on_startup()
    yield
    terminal_manager.sessions.clear()
    await Tortoise.close_connections()

# -------------------------------------------------------------------
# App
# -------------------------------------------------------------------

app = FastAPI(
    title="AI Project Builder API",
    version="1.0.0",
    lifespan=lifespan,
)

# -------------------------------------------------------------------
# Middleware
# -------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://code-seed-box.lovable.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(request_id_middleware)

# -------------------------------------------------------------------
# Routers
# -------------------------------------------------------------------

app.include_router(auth_router)
app.include_router(runtime_router)
app.include_router(management_router)
app.include_router(stats_router)


# -------------------------------------------------------------------
# Health
# -------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    try:
        await Tortoise.get_connection("default").execute_query("SELECT 1")
        return {"status": "ready"}
    except Exception as e:
        return {"status": "not_ready", "error": str(e)}

# -------------------------------------------------------------------
# Projects
# -------------------------------------------------------------------

@app.get("/projects", response_model=list[str])
async def list_projects(
    user=Depends(AuthDependency.get_current_user),
):
    projects = (
        await Project.all()
        if user.is_admin
        else await Project.filter(owner=user)
    )
    return sorted(p.name for p in projects)


@app.post(
    "/projects/generate",
    response_model=GenerateProjectResponse,
    dependencies=[Depends(project_generation_limit)],
)
async def generate_project(
    req: GenerateProjectRequest,
    user=Depends(AuthDependency.get_current_user),
):
    # ⚠️ Heavy operation → off event loop
    result = await asyncio.to_thread(run_agent, req.prompt)

    coder_state = result.get("coder_state")
    if not coder_state:
        raise HTTPException(
            status_code=500,
            detail="Project generation failed",
        )

    project_root = coder_state.project_root
    project_name = project_root.split("/")[-1]

    try:
        await Project.create(
            name=project_name,
            project_root=project_root,
            owner=user,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Project with the same name already exists",
        )

    return GenerateProjectResponse(
        project_name=project_name,
        project_root=project_root,
    )

# -------------------------------------------------------------------
# Files
# -------------------------------------------------------------------

@app.get(
    "/projects/{project_name}/files",
    response_model=ListFilesResponse,
    dependencies=[Depends(file_ops_limit)],
)
async def list_project_files(
    project_name: str,
    user=Depends(AuthDependency.get_current_user),
):
    project = await ensure_project_access(project_name, user)
    api_set_project_root(project.project_root)

    output = api_list_files(".")
    files = output.split("\n") if output and "No files found" not in output else []

    return ListFilesResponse(
        project_name=project_name,
        files=files,
    )


@app.get(
    "/projects/{project_name}/files/read",
    response_model=ReadFileResponse,
    dependencies=[Depends(file_ops_limit)],
)
async def read_project_file(
    project_name: str,
    file_path: str = Query(..., description="Relative file path"),
    user=Depends(AuthDependency.get_current_user),
):
    project = await ensure_project_access(project_name, user)
    api_set_project_root(project.project_root)

    content = api_read_file(file_path)
    if content.startswith("ERROR"):
        raise HTTPException(status_code=400, detail=content)

    return ReadFileResponse(
        project_name=project_name,
        file_path=file_path,
        content=content,
    )


@app.post(
    "/projects/{project_name}/files/write",
    dependencies=[Depends(file_ops_limit)],
)
async def write_project_file(
    project_name: str,
    file_path: str = Query(..., description="Relative file path"),
    payload: WriteFileRequest = Body(...),
    user=Depends(AuthDependency.get_current_user),
):
    project = await ensure_project_access(project_name, user)
    api_set_project_root(project.project_root)

    result = api_write_file(file_path, payload.content)
    if result.startswith("ERROR"):
        raise HTTPException(status_code=400, detail=result)

    return {"result": result}


@app.delete(
    "/projects/{project_name}/files/delete",
    dependencies=[Depends(file_ops_limit)],
)
async def delete_project_file(
    project_name: str,
    file_path: str = Query(..., description="Relative file path"),
    user=Depends(AuthDependency.get_current_user),
):
    project = await ensure_project_access(project_name, user)
    api_set_project_root(project.project_root)

    result = api_delete_file(file_path)
    if result.startswith("ERROR"):
        raise HTTPException(status_code=400, detail=result)

    return {"result": result}

# -------------------------------------------------------------------
# Folders
# -------------------------------------------------------------------

@app.post(
    "/projects/{project_name}/folders/create",
    dependencies=[Depends(file_ops_limit)],
)
async def create_project_folder(
    project_name: str,
    folder_path: str = Query(..., description="Relative folder path"),
    user=Depends(AuthDependency.get_current_user),
):
    project = await ensure_project_access(project_name, user)
    api_set_project_root(project.project_root)

    result = api_create_folder(folder_path)
    if result.startswith("ERROR"):
        raise HTTPException(status_code=400, detail=result)

    return {"result": result}


@app.delete(
    "/projects/{project_name}/folders/delete",
    dependencies=[Depends(file_ops_limit)],
)
async def delete_project_folder(
    project_name: str,
    folder_path: str = Query(..., description="Relative folder path"),
    user=Depends(AuthDependency.get_current_user),
):
    project = await ensure_project_access(project_name, user)
    api_set_project_root(project.project_root)

    result = api_delete_folder(folder_path)
    if result.startswith("ERROR"):
        raise HTTPException(status_code=400, detail=result)

    return {"result": result}

# -------------------------------------------------------------------
# Exceptions
# -------------------------------------------------------------------

@app.exception_handler(CommandRejected)
async def command_rejected_handler(_, exc: CommandRejected):
    return JSONResponse(
        status_code=422,
        content={
            "error": "command_rejected",
            "detail": str(exc),
        },
    )
