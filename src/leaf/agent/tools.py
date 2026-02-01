"""Tools available to the LEAF agent."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class CardProposal(BaseModel):
    """A proposed card that the agent wants to create."""

    name: str = Field(description="Short, descriptive name for the card")
    description: str = Field(description="What this card does")
    trigger_type: Literal["file_created", "file_modified", "schedule", "manual"] = Field(
        description="What triggers this card"
    )
    trigger_folder: str | None = Field(
        default=None, description="Folder to watch (relative to project root)"
    )
    trigger_pattern: str | None = Field(
        default=None, description="File pattern to match (e.g., '*.csv')"
    )
    code: str = Field(description="Python code to execute when triggered")
    dependencies: list[str] = Field(
        default_factory=list, description="Python packages required (e.g., ['pandas', 'numpy'])"
    )


class FileContent(BaseModel):
    """Content of a file."""

    path: str
    content: str
    exists: bool


class DirectoryListing(BaseModel):
    """Listing of files in a directory."""

    path: str
    files: list[str]
    directories: list[str]


def read_project_file(project_path: Path, relative_path: str) -> FileContent:
    """Read a file from the project.

    Args:
        project_path: The project root path
        relative_path: Path relative to project root

    Returns:
        FileContent with the file's content
    """
    file_path = (project_path / relative_path).resolve()

    # Security: ensure path is within project
    try:
        file_path.relative_to(project_path.resolve())
    except ValueError:
        return FileContent(
            path=relative_path,
            content="Error: Path is outside project folder",
            exists=False,
        )

    if not file_path.exists():
        return FileContent(path=relative_path, content="", exists=False)

    if not file_path.is_file():
        return FileContent(
            path=relative_path,
            content="Error: Path is not a file",
            exists=False,
        )

    try:
        content = file_path.read_text()
        return FileContent(path=relative_path, content=content, exists=True)
    except Exception as e:
        return FileContent(
            path=relative_path,
            content=f"Error reading file: {e}",
            exists=False,
        )


def write_project_file(project_path: Path, relative_path: str, content: str) -> str:
    """Write a file to the project.

    Args:
        project_path: The project root path
        relative_path: Path relative to project root
        content: Content to write

    Returns:
        Success message or error
    """
    file_path = (project_path / relative_path).resolve()

    # Security: ensure path is within project
    try:
        file_path.relative_to(project_path.resolve())
    except ValueError:
        return "Error: Path is outside project folder"

    # Don't allow writing to .leaf directory
    if ".leaf" in file_path.parts:
        return "Error: Cannot write to .leaf directory directly"

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return f"Successfully wrote {len(content)} bytes to {relative_path}"
    except Exception as e:
        return f"Error writing file: {e}"


def list_project_directory(project_path: Path, relative_path: str = ".") -> DirectoryListing:
    """List contents of a directory in the project.

    Args:
        project_path: The project root path
        relative_path: Path relative to project root

    Returns:
        DirectoryListing with files and subdirectories
    """
    # Resolve project path to handle symlinks (e.g., /var -> /private/var on macOS)
    resolved_project = project_path.resolve()
    dir_path = (resolved_project / relative_path).resolve()

    # Security: ensure path is within project
    try:
        dir_path.relative_to(resolved_project)
    except ValueError:
        return DirectoryListing(path=relative_path, files=[], directories=[])

    if not dir_path.exists() or not dir_path.is_dir():
        return DirectoryListing(path=relative_path, files=[], directories=[])

    files = []
    directories = []

    try:
        for entry in sorted(dir_path.iterdir()):
            # Skip hidden files and .leaf directory
            if entry.name.startswith("."):
                continue

            rel_entry = entry.relative_to(resolved_project)
            if entry.is_file():
                files.append(str(rel_entry))
            elif entry.is_dir():
                directories.append(str(rel_entry))
    except Exception:
        pass

    return DirectoryListing(path=relative_path, files=files, directories=directories)
