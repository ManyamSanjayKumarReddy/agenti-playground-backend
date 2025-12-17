import subprocess
from typing import List, Optional, Dict, Tuple

from agent_v1.runtime.command_policy import validate_command, CommandRejected
from agent_v1.runtime.registry import runtime_registry, RuntimeNotFound
from agent_v1.runtime.docker_manager import docker_manager, DockerError


class ExecutionError(Exception):
    pass


class CommandExecutor:
    """
    Executes validated commands inside a project's Docker container.
    """

    def exec(
        self,
        project_name: str,
        command: str,
        args: List[str],
        cwd: Optional[str] = None,
        timeout: int = 60,
        env: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, str, str]:
        """
        Execute a command inside the project's container.

        Returns:
            (return_code, stdout, stderr)
        """

        # 1. Validate runtime
        try:
            runtime = runtime_registry.get(project_name)
        except RuntimeNotFound as e:
            raise ExecutionError(str(e))

        if runtime.status != "running":
            raise ExecutionError(
                f"Runtime is not running for project: {project_name}"
            )

        if not runtime.container_id:
            raise ExecutionError("Container ID not available")

        # 2. Validate command against policy
        try:
            validate_command(command, args, cwd)
        except CommandRejected as e:
            raise ExecutionError(f"Command rejected: {str(e)}")

        # 3. Build docker exec command (NO SHELL)
        docker_cmd = [
            "docker",
            "exec",
        ]

        if env:
            for k, v in env.items():
                docker_cmd.extend(["-e", f"{k}={v}"])

        CONTAINER_WORKDIR = "/workspace"

        if cwd:
            if cwd == ".":
                abs_cwd = CONTAINER_WORKDIR
            else:
                abs_cwd = f"{CONTAINER_WORKDIR}/{cwd.lstrip('/')}"
            docker_cmd.extend(["-w", abs_cwd])

        docker_cmd.append(runtime.container_id)
        docker_cmd.append(command)
        docker_cmd.extend(args)

        # 4. Execute
        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise ExecutionError("Command execution timed out")
        except Exception as e:
            raise ExecutionError(str(e))

        # 5. Record execution
        runtime.record_command(
            " ".join([command] + args)
        )

        return (
            result.returncode,
            result.stdout.strip(),
            result.stderr.strip(),
        )


# Singleton
command_executor = CommandExecutor()
