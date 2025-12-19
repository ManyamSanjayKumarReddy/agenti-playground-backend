from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse

from tortoise import Tortoise

from agent_v1.graph.graph import run_agent
from agent_v1.api.schemas import (
    GenerateProjectRequest,
    GenerateProjectResponse,
    ListFilesResponse,
    ReadFileResponse,
    WriteFileRequest,
)
from agent_v1.api.project_utils import resolve_project_dir, GENERATED_PROJECTS_ROOT

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
from agent_v1.api.db.config import init_db
from agent_v1.runtime.reconcile import reconcile_runtimes_on_startup
from agent_v1.runtime.terminal_manager import terminal_manager
from agent_v1.core.logging import setup_logging
from agent_v1.core.middleware import request_id_middleware
from agent_v1.runtime.command_policy import CommandRejected
from agent_v1.api.admin_routes import router as admin_router

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------

setup_logging()

# -------------------------------------------------------------------
# Application Lifespan
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(request_id_middleware)

# -------------------------------------------------------------------
# Routers
# -------------------------------------------------------------------

app.include_router(runtime_router)
app.include_router(admin_router)


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
def list_projects():
    if not GENERATED_PROJECTS_ROOT.exists():
        return []

    return sorted(
        p.name for p in GENERATED_PROJECTS_ROOT.iterdir() if p.is_dir()
    )


@app.post("/projects/generate", response_model=GenerateProjectResponse)
def generate_project(req: GenerateProjectRequest):
    result = run_agent(req.prompt)

    coder_state = result.get("coder_state")
    if not coder_state:
        raise HTTPException(status_code=500, detail="Project generation failed")

    project_root = coder_state.project_root
    project_name = project_root.split("/")[-1]

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
)
def list_project_files(project_name: str):
    project_dir = resolve_project_dir(project_name)
    api_set_project_root(str(project_dir))

    output = api_list_files(".")
    files = (
        output.split("\n")
        if output and "No files found" not in output
        else []
    )

    return ListFilesResponse(
        project_name=project_name,
        files=files,
    )


@app.get(
    "/projects/{project_name}/files/read",
    response_model=ReadFileResponse,
)
def read_project_file(project_name: str, file_path: str):
    project_dir = resolve_project_dir(project_name)
    api_set_project_root(str(project_dir))

    content = api_read_file(file_path)
    if content.startswith("ERROR"):
        raise HTTPException(status_code=400, detail=content)

    return ReadFileResponse(
        project_name=project_name,
        file_path=file_path,
        content=content,
    )


@app.post("/projects/{project_name}/files/write")
def write_project_file(
    project_name: str,
    file_path: str,
    payload: WriteFileRequest = Body(...),
):
    project_dir = resolve_project_dir(project_name)
    api_set_project_root(str(project_dir))

    result = api_write_file(
        path=file_path,
        content=payload.content,
    )

    return {"result": result}


@app.delete("/projects/{project_name}/files/delete")
def delete_project_file(project_name: str, file_path: str):
    project_dir = resolve_project_dir(project_name)
    api_set_project_root(str(project_dir))

    result = api_delete_file(file_path)
    if result.startswith("ERROR"):
        raise HTTPException(status_code=400, detail=result)

    return {"result": result}

# -------------------------------------------------------------------
# Folders
# -------------------------------------------------------------------

@app.post("/projects/{project_name}/folders/create")
def create_project_folder(project_name: str, folder_path: str):
    project_dir = resolve_project_dir(project_name)
    api_set_project_root(str(project_dir))

    return {"result": api_create_folder(folder_path)}


@app.delete("/projects/{project_name}/folders/delete")
def delete_project_folder(project_name: str, folder_path: str):
    project_dir = resolve_project_dir(project_name)
    api_set_project_root(str(project_dir))

    result = api_delete_folder(folder_path)
    if result.startswith("ERROR"):
        raise HTTPException(status_code=400, detail=result)

    return {"result": result}

# -------------------------------------------------------------------
# Exception Handling
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
