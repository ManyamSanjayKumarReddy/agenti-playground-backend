import pathlib
import subprocess
from typing import Tuple, Optional
import os
# -------------------------------------------------------------------
# Project Root Configuration (API)
# -------------------------------------------------------------------

_API_PROJECT_ROOT: Optional[pathlib.Path] = None


def api_set_project_root(path: str):
    """Set the project root directory for API filesystem operations."""
    global _API_PROJECT_ROOT
    _API_PROJECT_ROOT = pathlib.Path(path).resolve()


def api_get_project_root() -> pathlib.Path:
    """Return the current API project root."""
    if _API_PROJECT_ROOT is None:
        raise RuntimeError("Project root not initialized")
    return _API_PROJECT_ROOT


# -------------------------------------------------------------------
# Path Safety Utilities (API)
# -------------------------------------------------------------------

def api_safe_path_for_project(path: str) -> pathlib.Path:
    """Ensure path stays within API project root."""
    if not path:
        raise ValueError("Path cannot be empty")

    root = api_get_project_root()
    candidate = (root / path).resolve()

    if candidate != root and root not in candidate.parents:
        raise ValueError("Attempt to access outside project root")

    return candidate



# -------------------------------------------------------------------
# File Operations (API)
# -------------------------------------------------------------------

# def api_write_file(path: str, content: str) -> str:
#     """Create or overwrite a file within the project root."""
#     p = api_safe_path_for_project(path)
#     p.parent.mkdir(parents=True, exist_ok=True)
#
#     with open(p, "w", encoding="utf-8") as f:
#         f.write(content)
#
#     return f"WROTE: {p.relative_to(api_get_project_root())}"

def api_write_file(path: str, content: str) -> str:
    p = api_safe_path_for_project(path)

    # Ensure parent directories exist
    p.parent.mkdir(parents=True, exist_ok=True)

    # FIX PERMISSIONS IF FILE EXISTS
    if p.exists():
        try:
            os.chmod(p, 0o666)
        except PermissionError:
            pass

    with open(p, "w", encoding="utf-8") as f:
        f.write(content)

    return f"WROTE: {p.relative_to(api_get_project_root())}"


def api_read_file(path: str) -> str:
    """Read file content within the project root."""
    p = api_safe_path_for_project(path)

    if not p.exists():
        return ""

    if not p.is_file():
        return f"ERROR: {path} is not a file"

    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def api_delete_file(path: str) -> str:
    """Delete a file within the project root."""
    p = api_safe_path_for_project(path)

    if not p.exists():
        return "ERROR: File does not exist"

    if not p.is_file():
        return f"ERROR: {path} is not a file"

    p.unlink()
    return f"DELETED_FILE: {path}"


# -------------------------------------------------------------------
# Folder Operations (API)
# -------------------------------------------------------------------

def api_create_folder(path: str) -> str:
    """Create a folder within the project root."""
    p = api_safe_path_for_project(path)
    p.mkdir(parents=True, exist_ok=True)
    return f"CREATED_FOLDER: {path}"


def api_delete_folder(path: str) -> str:
    """Recursively delete a folder within the project root."""
    p = api_safe_path_for_project(path)

    if not p.exists():
        return "ERROR: Folder does not exist"

    if not p.is_dir():
        return f"ERROR: {path} is not a directory"

    for item in sorted(p.glob("**/*"), reverse=True):
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            item.rmdir()

    p.rmdir()
    return f"DELETED_FOLDER: {path}"


# -------------------------------------------------------------------
# Listing (API)
# -------------------------------------------------------------------

def api_list_files(directory: str = ".") -> str:
    """Recursively list all files inside a directory."""
    p = api_safe_path_for_project(directory)

    if not p.exists():
        return f"ERROR: Directory does not exist: {directory}"

    if not p.is_dir():
        return f"ERROR: {directory} is not a directory"

    files = sorted(
        str(f.relative_to(api_get_project_root()))
        for f in p.glob("**/*")
        if f.is_file()
    )

    return "\n".join(files) if files else "No files found"


def api_get_current_directory() -> str:
    """Return project root path."""
    return str(api_get_project_root())

