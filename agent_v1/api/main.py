import io
import tarfile

from fastapi import FastAPI, HTTPException, Body, Query, Depends, Form, File, UploadFile
from fastapi.responses import JSONResponse, Response

from agent_v1.graph.graph import run_agent, run_modify
from agent_v1.api.schemas.graph import (
    GenerateProjectRequest,
    GenerateProjectResponse,
    ListFilesResponse,
    ReadFileResponse,
    WriteFileRequest,
    RenameFileRequest,
)

from agent_v1.tools.utils import (
    api_set_project_root,
    api_list_files,
    api_read_file,
    api_write_file,
    api_delete_file,
    api_create_folder,
    api_delete_folder,
    api_rename_item,
)

from agent_v1.api.project_utils import resolve_project_dir
from agent_v1.tools.project_root import GENERATED_PROJECTS_ROOT, create_project_root
from agent_v1.core.logging import setup_logging
from agent_v1.core.middleware import request_id_middleware
from agent_v1.core.internal_auth import require_internal_secret

import asyncio

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------

setup_logging()

# -------------------------------------------------------------------
# App
#
# This is an internal-only service — called by the ZeroTo control
# plane, not directly by end users/browsers. All routes except the
# health check require the shared internal secret.
# -------------------------------------------------------------------

app = FastAPI(
    title="Agentbay Generation Service",
    version="2.0.0",
)

app.middleware("http")(request_id_middleware)

# -------------------------------------------------------------------
# Health
# -------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}

# -------------------------------------------------------------------
# Exceptions
# -------------------------------------------------------------------

@app.exception_handler(FileNotFoundError)
async def project_not_found_handler(_, exc: FileNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def bad_project_path_handler(_, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})

# -------------------------------------------------------------------
# Projects
# -------------------------------------------------------------------

@app.get(
    "/projects",
    response_model=list[str],
    dependencies=[Depends(require_internal_secret)],
)
async def list_projects():
    if not GENERATED_PROJECTS_ROOT.exists():
        return []
    return sorted(p.name for p in GENERATED_PROJECTS_ROOT.iterdir() if p.is_dir())


@app.post(
    "/projects/generate",
    response_model=GenerateProjectResponse,
    dependencies=[Depends(require_internal_secret)],
)
async def generate_project(req: GenerateProjectRequest):
    # Heavy operation -> off the event loop
    result = await asyncio.to_thread(run_agent, req.prompt)

    coder_state = result.get("coder_state")
    if not coder_state:
        raise HTTPException(
            status_code=500,
            detail="Project generation failed",
        )

    project_root = coder_state.project_root
    project_name = project_root.split("/")[-1]

    return GenerateProjectResponse(
        project_name=project_name,
        project_root=project_root,
    )


@app.get(
    "/projects/{project_name}/archive",
    dependencies=[Depends(require_internal_secret)],
)
async def archive_project(project_name: str):
    """
    Returns the whole generated project as an uncompressed tar, contents
    rooted at the tar root (not nested under the project name) — so the
    caller can extract it straight into a target directory, e.g.
    `tar -xf - -C <hostPath>`. Used by ZeroTo's projectGeneratorWorker to
    hand a generated project off to a node's volume in one bulk transfer.
    """
    project_dir = resolve_project_dir(project_name)

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        tar.add(project_dir, arcname=".")

    return Response(content=buffer.getvalue(), media_type="application/x-tar")


@app.post(
    "/projects/modify",
    dependencies=[Depends(require_internal_secret)],
)
async def modify_project(
    prompt: str = Form(...),
    archive: UploadFile = File(...),
):
    """
    One synchronous round trip: extracts the uploaded tar (the CURRENT
    state of a project the caller already generated elsewhere - agentbay
    has no memory of its own past generations) into a fresh scratch
    directory, runs the modify graph against it, and returns the updated
    project as a tar in the same shape /projects/{name}/archive does.
    No project name/slug involved - the caller doesn't need one since
    there's nothing to poll for, unlike /projects/generate.
    """
    project_dir = create_project_root("modify")

    tar_bytes = await archive.read()
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r") as tar:
        tar.extractall(project_dir)

    result = await asyncio.to_thread(run_modify, str(project_dir), prompt)

    coder_state = result.get("coder_state")
    if not coder_state:
        raise HTTPException(status_code=500, detail="Project modification failed")

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as out_tar:
        out_tar.add(project_dir, arcname=".")

    return Response(content=buffer.getvalue(), media_type="application/x-tar")

# -------------------------------------------------------------------
# Files
# -------------------------------------------------------------------

@app.get(
    "/projects/{project_name}/files",
    response_model=ListFilesResponse,
    dependencies=[Depends(require_internal_secret)],
)
async def list_project_files(project_name: str):
    api_set_project_root(resolve_project_dir(project_name))

    output = api_list_files(".")
    files = output.split("\n") if output and "No files found" not in output else []

    return ListFilesResponse(
        project_name=project_name,
        files=files,
    )


@app.get(
    "/projects/{project_name}/files/read",
    response_model=ReadFileResponse,
    dependencies=[Depends(require_internal_secret)],
)
async def read_project_file(
    project_name: str,
    file_path: str = Query(..., description="Relative file path"),
):
    api_set_project_root(resolve_project_dir(project_name))

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
    dependencies=[Depends(require_internal_secret)],
)
async def write_project_file(
    project_name: str,
    file_path: str = Query(..., description="Relative file path"),
    payload: WriteFileRequest = Body(...),
):
    api_set_project_root(resolve_project_dir(project_name))

    result = api_write_file(file_path, payload.content)
    if result.startswith("ERROR"):
        raise HTTPException(status_code=400, detail=result)

    return {"result": result}


@app.delete(
    "/projects/{project_name}/files/delete",
    dependencies=[Depends(require_internal_secret)],
)
async def delete_project_file(
    project_name: str,
    file_path: str = Query(..., description="Relative file path"),
):
    api_set_project_root(resolve_project_dir(project_name))

    result = api_delete_file(file_path)
    if result.startswith("ERROR"):
        raise HTTPException(status_code=400, detail=result)

    return {"result": result}


@app.put(
    "/projects/{project_name}/files/rename",
    dependencies=[Depends(require_internal_secret)],
)
async def rename_project_item(
    project_name: str,
    payload: RenameFileRequest = Body(...),
):
    api_set_project_root(resolve_project_dir(project_name))

    result = api_rename_item(payload.old_path, payload.new_path)
    if result.startswith("ERROR"):
        raise HTTPException(status_code=400, detail=result)

    return {"result": result}

# -------------------------------------------------------------------
# Folders
# -------------------------------------------------------------------

@app.post(
    "/projects/{project_name}/folders/create",
    dependencies=[Depends(require_internal_secret)],
)
async def create_project_folder(
    project_name: str,
    folder_path: str = Query(..., description="Relative folder path"),
):
    api_set_project_root(resolve_project_dir(project_name))

    result = api_create_folder(folder_path)
    if result.startswith("ERROR"):
        raise HTTPException(status_code=400, detail=result)

    return {"result": result}


@app.delete(
    "/projects/{project_name}/folders/delete",
    dependencies=[Depends(require_internal_secret)],
)
async def delete_project_folder(
    project_name: str,
    folder_path: str = Query(..., description="Relative folder path"),
):
    api_set_project_root(resolve_project_dir(project_name))

    result = api_delete_folder(folder_path)
    if result.startswith("ERROR"):
        raise HTTPException(status_code=400, detail=result)

    return {"result": result}
