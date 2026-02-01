# LEAF - Claude Context

## What is LEAF?

LEAF (Local Event-Driven Automation Framework) is a desktop app that lets users create automations through natural language. Think "Claude Cowork meets HyperCard" — users describe what they want, an LLM generates Python code, and that code runs automatically when files are added to watched folders.

## Core Workflow

1. User: "Analyze CSV files dropped in inbox/ and generate reports"
2. LEAF agent generates a Python program and creates a Card
3. When a CSV appears in inbox/, the Card triggers
4. Python runs via `uv run`, output appears in Event Queue

## Tech Stack

| Layer | Technology |
|-------|------------|
| Desktop Shell | Tauri 2.x |
| Backend | FastAPI (Python) |
| Package Manager | UV |
| AI Framework | PydanticAI |
| Model Access | Pydantic AI Gateway |
| Workflow Engine | Temporal |
| Database | SQLite via SQLModel |
| File Watching | watchfiles |
| Frontend | React + TypeScript |

## Project Structure

```
leaf/
├── context/
│   └── LEAF_SPEC.md          # Full specification (read this for details)
├── tauri/                     # Tauri shell (Rust)
├── frontend/                  # React frontend
├── src/leaf/                  # Python backend
│   ├── api/                   # FastAPI routes + WebSocket
│   ├── core/                  # Config, event bus
│   ├── workspace/             # Workspace + file watcher
│   ├── cards/                 # Card models + registry
│   ├── execution/             # Sandbox + Temporal workflows
│   ├── agent/                 # PydanticAI agent + prompts
│   ├── mcp/                   # MCP server management
│   └── db/                    # SQLModel schemas
├── tests/
├── pyproject.toml
└── uv.lock
```

## Key Commands

```bash
# Setup
uv sync                                    # Install Python deps
cd frontend && npm install                 # Install frontend deps

# Development
temporal server start-dev                  # Start Temporal (terminal 1)
uv run uvicorn leaf.main:app --reload     # Start backend (terminal 2)
cd tauri && cargo tauri dev               # Start Tauri (terminal 3)

# Testing
uv run pytest                             # Run tests
uv run ruff check .                       # Lint

# Dependencies
uv add <package>                          # Add dependency
uv add --group dev <package>              # Add dev dependency
```

## Key Concepts

### Cards
A Card is an automation: trigger + generated Python code + execution settings. Cards are stored as JSON in `.leaf/cards/` and their programs in `.leaf/programs/`.

### Event Queue
All events (file changes, card executions, agent responses) flow through a central queue visible in the UI. WebSocket streams events to the frontend in real-time.

### Interaction Primitives
The LLM can only use a fixed set of inputs/outputs (confirmation, choice, text_input, etc.) — no freeform UI generation. This keeps behavior predictable.

### Sandboxed Execution
Generated programs run via `uv run` in isolated environments. Each card has its own `pyproject.toml` and `uv.lock`. Programs can only write to the workspace folder.

## Environment Variables

```bash
PYDANTIC_AI_GATEWAY_API_KEY=xxx   # Required: AI Gateway key
LEAF_PORT=8000                     # Optional: API port
LEAF_MODEL=gateway/google:gemini-2.5-flash  # Optional: default model
```

## Implementation Status

Not yet started. See `context/LEAF_SPEC.md` for full specification and implementation phases.

## Important Files

- `context/LEAF_SPEC.md` — Full specification with architecture, schemas, and implementation details
- `src/leaf/agent/leaf_agent.py` — PydanticAI agent (will generate cards + code)
- `src/leaf/execution/workflows.py` — Temporal workflows for card execution
- `src/leaf/cards/models.py` — Card and Trigger Pydantic models

## Code Style

- Python 3.11+
- Use `uv` for all package management
- Pydantic models for all data structures
- Async everywhere (FastAPI, Temporal activities)
- Type hints required
- Ruff for linting (E, F, I, UP rules)
