"""Card and Trigger Pydantic models.

These are the API-level models used for request/response handling.
The SQLModel Card is used for database persistence.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class TriggerConfig(BaseModel):
    """Configuration for a card's trigger.

    Defines when the card should be activated.
    """

    type: Literal["file_created", "file_modified", "schedule", "manual"]
    folder: str | None = None  # Relative to project root
    pattern: str | None = None  # Glob pattern, e.g., "*.csv"
    cron: str | None = None  # For schedule triggers


class ProgramConfig(BaseModel):
    """Configuration for a card's generated program."""

    language: Literal["python"] = "python"
    entrypoint: str = "main.py"
    dependencies: list[str] = Field(default_factory=list)


class CardCreate(BaseModel):
    """Request model for creating a new card."""

    name: str
    description: str | None = None
    user_prompt: str
    trigger_config: TriggerConfig
    program_config: ProgramConfig = Field(default_factory=ProgramConfig)
    timeout_seconds: int = 300
    retry_count: int = 3
    enabled: bool = True
    allowed_outputs: list[str] = Field(
        default_factory=lambda: ["message", "progress", "file_created"]
    )


class CardUpdate(BaseModel):
    """Request model for updating a card.

    All fields are optional - only provided fields will be updated.
    """

    name: str | None = None
    description: str | None = None
    trigger_config: TriggerConfig | None = None
    program_config: ProgramConfig | None = None
    timeout_seconds: int | None = None
    retry_count: int | None = None
    enabled: bool | None = None
    allowed_outputs: list[str] | None = None


class CardDetailResponse(BaseModel):
    """Detailed card response including all fields."""

    id: str
    name: str
    description: str | None
    user_prompt: str
    trigger_config: dict[str, Any]
    program_config: dict[str, Any]
    program_path: str
    timeout_seconds: int
    retry_count: int
    enabled: bool
    allowed_outputs: list[str]
    created_at: str
    updated_at: str
    last_run_at: str | None
    run_count: int


class TriggerResult(BaseModel):
    """Result of evaluating whether an event matches a card's trigger."""

    matches: bool
    card_id: str
    reason: str | None = None  # Why it matched or didn't match
