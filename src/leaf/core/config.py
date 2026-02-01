"""App-level configuration management.

Manages ~/.leaf/config.json for app-wide settings.
"""

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


def get_config_dir() -> Path:
    """Get the app config directory (~/.leaf or LEAF_CONFIG_DIR)."""
    config_dir = os.environ.get("LEAF_CONFIG_DIR")
    if config_dir:
        path = Path(config_dir).expanduser()
    else:
        path = Path.home() / ".leaf"
    return path


class ApiKeys(BaseModel):
    """API keys for external services."""

    pydantic_ai_gateway: str | None = None


class AppConfig(BaseModel):
    """App-level configuration stored in ~/.leaf/config.json."""

    version: str = "1.0"
    theme: Literal["light", "dark", "system"] = "system"
    default_model: str = "gateway/google:gemini-2.5-flash"
    api_keys: ApiKeys = Field(default_factory=ApiKeys)
    telemetry: bool = False


def get_app_config() -> AppConfig:
    """Load app configuration from ~/.leaf/config.json.

    Creates default config if it doesn't exist.
    """
    config_dir = get_config_dir()
    config_file = config_dir / "config.json"

    if not config_file.exists():
        # Create default config
        config_dir.mkdir(parents=True, exist_ok=True)
        config = AppConfig()
        save_app_config(config)
        return config

    with open(config_file) as f:
        data = json.load(f)

    return AppConfig.model_validate(data)


def save_app_config(config: AppConfig) -> None:
    """Save app configuration to ~/.leaf/config.json."""
    config_dir = get_config_dir()
    config_file = config_dir / "config.json"

    config_dir.mkdir(parents=True, exist_ok=True)

    with open(config_file, "w") as f:
        json.dump(config.model_dump(), f, indent=2)
