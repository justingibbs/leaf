"""Database session management for per-project SQLite databases.

Each project has its own database at .leaf/leaf.db.
"""

from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from leaf.db.models import Card, ChatMessage, Event, Execution, MCPServer  # noqa: F401

# Cache of engines by database path
_engines: dict[str, any] = {}


def get_engine(database_path: Path):
    """Get or create a SQLite engine for the given database path."""
    path_str = str(database_path.resolve())

    if path_str not in _engines:
        # Ensure parent directory exists
        database_path.parent.mkdir(parents=True, exist_ok=True)

        # Create engine with SQLite-specific settings
        engine = create_engine(
            f"sqlite:///{path_str}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        _engines[path_str] = engine

    return _engines[path_str]


def init_database(database_path: Path) -> None:
    """Initialize the database schema for a project.

    Creates all tables if they don't exist.
    """
    engine = get_engine(database_path)
    SQLModel.metadata.create_all(engine)


def get_session(database_path: Path) -> Generator[Session, None, None]:
    """Get a database session for the given project database.

    Usage:
        with get_session(db_path) as session:
            session.add(...)
            session.commit()
    """
    engine = get_engine(database_path)
    with Session(engine) as session:
        yield session


def close_engine(database_path: Path) -> None:
    """Close and remove the engine for a database path."""
    path_str = str(database_path.resolve())
    if path_str in _engines:
        _engines[path_str].dispose()
        del _engines[path_str]
