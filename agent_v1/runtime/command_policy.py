import re
from typing import List, Dict


class CommandRejected(Exception):
    """Raised when a command violates security policy."""

# BLOCKED PATTERNS (GLOBAL)
BLOCKED_PATTERNS = [
    r";",              # command chaining
    r"&&",
    r"\|\|",
    r"\|",
    r"`",              # command substitution
    r"\$\(",
    r"\.\.",           # path traversal
    r"~",              # home directory
    r"/",              # absolute paths
    r"sudo",
    r"ssh",
    r"scp",
    r"curl",
    r"wget",
    r"rm\s+-rf",
    r"chmod",
    r"chown",
    r"kill",
    r"pkill",
    r"mount",
    r"umount",
]

# ALLOWED COMMANDS
ALLOWED_COMMANDS: Dict[str, Dict] = {
    "python": {
        "allowed_args": ["-m"],
        "allow_any_args": True
    },
    "pip": {
        "allowed_args": ["install", "list", "freeze", "-r"],
        "allow_any_args": False
    },
    "npm": {
        "allowed_args": ["install", "run"],
        "allow_any_args": True
    },
    "npx": {
        "allowed_args": [],
        "allow_any_args": True
    },
    "node": {
        "allowed_args": [],
        "allow_any_args": True
    },
    "uvicorn": {
        "allowed_args": [],
        "allow_any_args": True
    },
    "pytest": {
        "allowed_args": [],
        "allow_any_args": True
    },
}

# VALIDATION FUNCTIONS
def _check_blocked_patterns(value: str):
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, value):
            raise CommandRejected(
                f"Blocked pattern detected: `{pattern}`"
            )

def validate_command(command: str, args: List[str], cwd: str | None = None):
    """
    Validates a structured command before execution.

    Parameters:
        command: base command (e.g., npm, python)
        args: list of arguments
        cwd: working directory (relative only)

    Raises:
        CommandRejected if validation fails
    """

    if not command:
        raise CommandRejected("Command cannot be empty")

    if command not in ALLOWED_COMMANDS:
        raise CommandRejected(f"Command not allowed: {command}")

    # Validate command string
    _check_blocked_patterns(command)

    # Validate args
    for arg in args:
        _check_blocked_patterns(arg)

    # Validate cwd
    if cwd:
        _check_blocked_patterns(cwd)
        if cwd.startswith("/"):
            raise CommandRejected("Absolute paths are not allowed")

    # Argument allowlist enforcement
    policy = ALLOWED_COMMANDS[command]

    if not policy["allow_any_args"]:
        for arg in args:
            if arg not in policy["allowed_args"]:
                raise CommandRejected(
                    f"Argument not allowed for `{command}`: {arg}"
                )

    return True
