from tortoise import fields
from tortoise.models import Model

class ProjectRuntime(Model):
    """
    Persistent runtime state for each generated project.
    """

    id = fields.UUIDField(pk=True)

    project_name = fields.CharField(
        max_length=255,
        unique=True,
        index=True
    )

    project_root = fields.TextField()

    container_name = fields.CharField(
        max_length=255,
        unique=True
    )

    image = fields.CharField(
        max_length=255,
        default="python:3.11-slim"
    )

    status = fields.CharField(
        max_length=32,
        default="stopped"
    )

    last_command = fields.TextField(
        null=True
    )

    created_at = fields.DatetimeField(
        auto_now_add=True
    )

    updated_at = fields.DatetimeField(
        auto_now=True
    )

    class Meta:
        table = "project_runtime"

    def __str__(self):
        return f"<Runtime {self.project_name} ({self.status})>"
