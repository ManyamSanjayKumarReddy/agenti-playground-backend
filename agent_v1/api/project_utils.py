import pathlib
from agent_v1.tools.project_root import GENERATED_PROJECTS_ROOT

def resolve_project_dir(project_name: str) -> pathlib.Path:
    """
    Resolves an existing project directory by name.
    """
    project_dir = GENERATED_PROJECTS_ROOT / project_name

    if not project_dir.exists():
        raise FileNotFoundError(f"Project not found: {project_name}")

    if not project_dir.is_dir():
        raise ValueError(f"Invalid project directory: {project_name}")

    return project_dir.resolve()
