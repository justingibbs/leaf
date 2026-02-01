"""SQLModel database models for per-project SQLite database.

Each project has its own database at .leaf/leaf.db containing these tables.
"""

from datetime import datetime
from typing import Any

from pydantic import field_validator
from sqlmodel import JSON, Column, Field, SQLModel


class Card(SQLModel, table=True):
    """An automation: trigger + generated code + settings."""

    __tablename__ = "cards"

    id: str = Field(primary_key=True)
    name: str
    description: str | None = None
    user_prompt: str
    trigger_config: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    program_config: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    program_path: str
    timeout_seconds: int = Field(default=300)
    retry_count: int = Field(default=3)
    enabled: bool = Field(default=True)
    allowed_outputs: list[str] = Field(
        sa_column=Column(JSON, nullable=False),
        default_factory=lambda: ["message", "progress", "file_created"],
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_run_at: datetime | None = None
    run_count: int = Field(default=0)


class Event(SQLModel, table=True):
    """Immutable record of something that happened."""

    __tablename__ = "events"

    id: str = Field(primary_key=True)
    type: str = Field(index=True)
    timestamp: datetime = Field(default_factory=datetime.now, index=True)
    payload: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    status: str = Field(default="pending", index=True)  # pending, processing, completed, failed
    matched_cards: list[str] | None = Field(sa_column=Column(JSON), default=None)
    execution_id: str | None = Field(default=None, foreign_key="executions.id")
    parent_event_id: str | None = Field(default=None, foreign_key="events.id")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"pending", "processing", "completed", "failed"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v


class Execution(SQLModel, table=True):
    """A single run of a card's program."""

    __tablename__ = "executions"

    id: str = Field(primary_key=True)
    card_id: str = Field(foreign_key="cards.id", index=True)
    event_id: str | None = Field(default=None, foreign_key="events.id")
    status: str = Field(index=True)  # pending, running, completed, failed
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = Field(sa_column=Column(JSON), default=None)
    error: str | None = None
    stdout: str | None = None
    stderr: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"pending", "running", "completed", "failed"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v


class MCPServer(SQLModel, table=True):
    """MCP server configuration for a project."""

    __tablename__ = "mcp_servers"

    id: str = Field(primary_key=True)
    name: str
    type: str  # stdio, http
    command: str | None = None
    args: list[str] | None = Field(sa_column=Column(JSON), default=None)
    url: str | None = None
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)


class ChatMessage(SQLModel, table=True):
    """Chat message in a project's conversation history."""

    __tablename__ = "chat_messages"

    id: str = Field(primary_key=True)
    role: str  # user, assistant
    content: str
    message_metadata: dict[str, Any] | None = Field(sa_column=Column(JSON), default=None)
    created_at: datetime = Field(default_factory=datetime.now, index=True)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"user", "assistant"}
        if v not in allowed:
            raise ValueError(f"role must be one of {allowed}")
        return v
