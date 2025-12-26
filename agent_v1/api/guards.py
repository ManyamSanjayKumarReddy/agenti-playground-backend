from fastapi import HTTPException, status
from agent_v1.api.db.models import Project
from agent_v1.api.db.models import User


async def ensure_project_access(
    project_name: str,
    user: User,
) -> Project:
    # 1. Authentication check
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # 2. Project existence check
    project = await Project.get_or_none(name=project_name)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # 3. Authorization check
    if user.is_admin or project.owner_id == user.id:
        return project

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have access to this project",
    )
