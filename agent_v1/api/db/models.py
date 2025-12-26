from tortoise import fields
from tortoise.models import Model

class User(Model):
    id = fields.UUIDField(pk=True)

    username = fields.CharField(max_length=50, unique=True, index=True)
    name = fields.CharField(max_length=100)
    email = fields.CharField(max_length=255, unique=True)
    phone = fields.CharField(max_length=20, unique=True)

    current_status = fields.CharField(
        max_length=32,
        description="job | student | other",
    )

    password_hash = fields.CharField(max_length=255)

    is_admin = fields.BooleanField(default=False)
    is_active = fields.BooleanField(default=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"


class RefreshToken(Model):
    id = fields.UUIDField(pk=True)

    user = fields.ForeignKeyField(
        "models.User",
        related_name="refresh_tokens",
        on_delete=fields.CASCADE,
    )

    hashed_token = fields.CharField(max_length=60, unique=True)
    jti = fields.CharField(max_length=36, unique=True)

    expires_at = fields.DatetimeField()
    is_revoked = fields.BooleanField(default=False)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "refresh_tokens"

class Project(Model):
    id = fields.UUIDField(pk=True)

    name = fields.CharField(max_length=255, index=True)
    project_root = fields.CharField(max_length=1024)

    owner = fields.ForeignKeyField(
        "models.User",
        related_name="projects",
        on_delete=fields.CASCADE,
    )

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "projects"
        unique_together = (("owner", "name"),)

    def __str__(self):
        return f"<Project {self.name}>"


class ProjectRuntime(Model):
    """
    Persistent runtime state for each generated project.

    Design Principles:
    ------------------
    - Backend manages ONLY the Docker container lifecycle.
    - Application processes (Flask / FastAPI / Streamlit / agents)
      are user-controlled via WebSocket terminal.
    - No backend-level process tracking is performed.

    This model intentionally avoids process-level state
    to prevent false or misleading runtime information.
    """

    id = fields.UUIDField(pk=True)

    # Unique project identifier (matches generated project folder)
    project = fields.OneToOneField(
        "models.Project",
        related_name="runtime",
        on_delete=fields.CASCADE,
    )

    # Absolute path to project directory on host
    project_root = fields.TextField()

    # Docker container name bound to this project
    container_name = fields.CharField(
        max_length=255,
        unique=True,
    )

    # Base image used for the container runtime
    image = fields.CharField(
        max_length=255,
        default="python:3.11-slim",
    )

    # Docker container lifecycle state
    # Values: running | stopped
    status = fields.CharField(
        max_length=32,
        default="stopped",
    )

    # Optional audit field for last executed command
    # (purely informational, not a source of truth)
    last_command = fields.TextField(
        null=True,
    )

    # Metadata
    created_at = fields.DatetimeField(
        auto_now_add=True,
    )

    updated_at = fields.DatetimeField(
        auto_now=True,
    )

    class Meta:
        table = "project_runtime"

    def __str__(self):
        return f"<Runtime {self.project_name} ({self.status})>"
