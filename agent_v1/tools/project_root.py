import pathlib
import re
from datetime import datetime

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
GENERATED_PROJECTS_ROOT = PROJECT_ROOT / "generated_projects"


def slugify(name :str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_" , name)
    return name.strip("_")

def create_project_root(project_name: str) -> pathlib.Path:
    GENERATED_PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)

    slug = slugify(project_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    project_dir = GENERATED_PROJECTS_ROOT / f"{slug}_{timestamp}"
    project_dir.mkdir(parents=True, exist_ok=False)

    return project_dir.resolve()



