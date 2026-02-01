"""App-level configuration management.

Manages ~/.leaf/config.json for app-wide settings.
Also loads environment variables from .env files.
"""

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

# Load .env file if it exists
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def get_config_dir() -> Path:
    """Get the app config directory (~/.leaf or LEAF_CONFIG_DIR)."""
    config_dir = os.environ.get("LEAF_CONFIG_DIR")
    if config_dir:
        path = Path(config_dir).expanduser()
    else:
        path = Path.home() / ".leaf"
    return path


def get_ai_api_key() -> str | None:
    """Get the AI API key from environment or config.

    Checks in order:
    1. PYDANTIC_AI_API_KEY environment variable
    2. App config file
    """
    # Check environment first
    api_key = os.environ.get("PYDANTIC_AI_API_KEY")
    if api_key:
        return api_key

    # Fall back to config file
    try:
        config = get_app_config()
        return config.api_keys.pydantic_ai_gateway
    except Exception:
        return None


def get_default_model() -> str:
    """Get the default AI model from environment or config.

    Checks in order:
    1. LEAF_MODEL environment variable
    2. App config file
    3. Default value
    """
    model = os.environ.get("LEAF_MODEL")
    if model:
        return model

    try:
        config = get_app_config()
        return config.default_model
    except Exception:
        return "google-gla:gemini-2.0-flash"


class ApiKeys(BaseModel):
    """API keys for external services."""

    pydantic_ai_gateway: str | None = None


class AppConfig(BaseModel):
    """App-level configuration stored in ~/.leaf/config.json."""

    version: str = "1.0"
    theme: Literal["light", "dark", "system"] = "system"
    default_model: str = "google-gla:gemini-2.0-flash"
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
