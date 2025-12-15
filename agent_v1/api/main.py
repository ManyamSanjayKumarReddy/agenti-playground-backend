from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from agent_v1.graph.graph import run_agent
from agent_v1.api.schemas import (
    GenerateProjectRequest,
    GenerateProjectResponse,
    ListFilesResponse,
    ReadFileResponse,
)
from agent_v1.api.project_utils import resolve_project_dir, GENERATED_PROJECTS_ROOT
from agent_v1.tools.filesystem import set_project_root, list_files, read_file


app = FastAPI(
    title="AI Project Builder API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """
    Health check endpoint.
    """
    return {
        "status": "ok",
        "service": "AI Project Builder API",
        "version": "1.0.0"
    }

@app.get("/projects", response_model=List[str])
def list_all_projects():
    """
    Lists all existing generated projects.
    """
    if not GENERATED_PROJECTS_ROOT.exists():
        return []

    projects = sorted(
        p.name
        for p in GENERATED_PROJECTS_ROOT.iterdir()
        if p.is_dir()
    )

    return projects

@app.post(
    "/projects/generate",
    response_model=GenerateProjectResponse
)
def generate_project(req: GenerateProjectRequest):
    """
    Generates a new project using LangGraph.
    """
    result = run_agent(req.prompt)

    coder_state = result.get("coder_state")
    if not coder_state:
        raise HTTPException(status_code=500, detail="Project generation failed")

    project_root = coder_state.project_root
    project_name = project_root.split("/")[-1]

    return GenerateProjectResponse(
        project_name=project_name,
        project_root=project_root
    )


@app.get(
    "/projects/{project_name}/files",
    response_model=ListFilesResponse
)
def list_project_files(project_name: str):
    """
    Lists all generated files for a project.
    """
    try:
        project_dir = resolve_project_dir(project_name)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    set_project_root(str(project_dir))
    files_output = list_files.run(".")

    files = (
        files_output.split("\n")
        if files_output and "No files found" not in files_output
        else []
    )

    return ListFilesResponse(
        project_name=project_name,
        files=files
    )


@app.get(
    "/projects/{project_name}/files/read",
    response_model=ReadFileResponse
)
def read_project_file(project_name: str, file_path: str):
    """
    Reads and displays a file from a project.
    """
    try:
        project_dir = resolve_project_dir(project_name)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    set_project_root(str(project_dir))
    content = read_file.run(file_path)

    if content.startswith("ERROR"):
        raise HTTPException(status_code=400, detail=content)

    return ReadFileResponse(
        project_name=project_name,
        file_path=file_path,
        content=content
    )


