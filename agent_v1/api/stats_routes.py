from fastapi import APIRouter, Depends
from pydantic import BaseModel

from agent_v1.api.auth.dependencies import AuthDependency
from agent_v1.api.db.models import Project, ProjectRuntime

router = APIRouter(
    prefix="/stats",
    tags=["stats"],
)

# -------------------------------------------------------------------
# Response Models
# -------------------------------------------------------------------

class ProjectStats(BaseModel):
    total: int
    with_runtime: int
    without_runtime: int


class RuntimeStats(BaseModel):
    total: int
    running: int
    stopped: int


class ContainerStats(BaseModel):
    running: int
    stopped: int


class SystemHealth(BaseModel):
    status: str


class StatsResponse(BaseModel):
    projects: ProjectStats
    runtimes: RuntimeStats
    containers: ContainerStats
    health: SystemHealth


# -------------------------------------------------------------------
# Stats Endpoint
# -------------------------------------------------------------------

@router.get("", response_model=StatsResponse)
async def get_user_stats(
    user=Depends(AuthDependency.get_current_user),
):
    # -------------------------
    # Projects
    # -------------------------
    projects = await Project.filter(owner=user).all()
    project_ids = [p.id for p in projects]

    total_projects = len(projects)

    runtimes = (
        await ProjectRuntime
        .filter(project_id__in=project_ids)
        .select_related("project")
    )

    runtime_count = len(runtimes)

    # -------------------------
    # Runtime states
    # -------------------------
    running = sum(1 for r in runtimes if r.status == "running")
    stopped = sum(1 for r in runtimes if r.status == "stopped")

    # -------------------------
    # Response
    # -------------------------
    return StatsResponse(
        projects=ProjectStats(
            total=total_projects,
            with_runtime=runtime_count,
            without_runtime=total_projects - runtime_count,
        ),
        runtimes=RuntimeStats(
            total=runtime_count,
            running=running,
            stopped=stopped,
        ),
        containers=ContainerStats(
            running=running,
            stopped=stopped,
        ),
        health=SystemHealth(status="ok"),
    )
