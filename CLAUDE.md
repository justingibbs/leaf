# LEAF - Claude Context

## What is LEAF?

LEAF (Local Event-Driven Automation Framework) is a desktop app that lets users create automations through natural language. Think "Claude Cowork meets HyperCard" — users describe what they want, an LLM generates Python code, and that code runs automatically when files are added to watched folders.

## Architecture

LEAF uses a two-level structure:

- **App Level** (`~/.leaf/`): Installed once, manages multiple projects
- **Project Level** (`.leaf/` in each project folder): Self-contained with own database, cards, queue

Projects are portable — zip and move to another machine.

## Core Workflow

1. User opens LEAF → selects or creates a **Project** (a folder)
2. User: "Analyze CSV files dropped in inbox/ and generate reports"
3. LEAF agent generates a Python program and creates a Card
4. When a CSV appears in inbox/, the Card triggers
5. Python runs via `uv run`, output appears in Event Queue

## Tech Stack

| Layer | Technology |
|-------|------------|
| Desktop Shell | Tauri 2.x |
| Backend | FastAPI (Python) |
| Package Manager | UV |
| AI Framework | PydanticAI |
| Model Access | Pydantic AI Gateway |
| Workflow Engine | Temporal |
| Database | SQLite via SQLModel (per-project) |
| File Watching | watchfiles |
| Frontend | React + TypeScript |

## Project Structure

```
leaf/
├── context/
│   ├── LEAF_SPEC.md          # Full specification (v2.2)
│   └── CONCEPTS.md           # Concepts & Synchronizations model
├── tauri/                     # Tauri shell (Rust)
├── frontend/                  # React frontend
├── src/leaf/                  # Python backend
│   ├── api/
│   │   ├── app_routes.py     # App-level routes (/api/app, /api/projects)
│   │   ├── project_routes.py # Project-level routes (/api/cards, etc.)
│   │   └── websocket.py      # WebSocket handler
│   ├── core/                  # Config, event bus
│   ├── projects/              # Project manager, registry, context
│   ├── watcher/               # File watcher
│   ├── cards/                 # Card models + registry
│   ├── execution/             # Sandbox + Temporal workflows
│   ├── agent/                 # PydanticAI agent + prompts
│   ├── mcp/                   # MCP server management
│   └── db/                    # SQLModel schemas (per-project)
├── tests/
├── pyproject.toml
└── uv.lock
```

## App vs Project Config

```
~/.leaf/                      # App-level (one per machine)
├── config.json               # Theme, default model, API keys
└── projects.json             # Registry of known projects

~/Documents/MyProject/        # Project folder (user's folder)
└── .leaf/                    # Project data
    ├── config.json           # Project settings
    ├── leaf.db               # SQLite (cards, events, executions)
    ├── programs/             # Generated Python programs
    ├── logs/                 # Execution logs
    └── outputs/              # Generated files
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

LEAF is built using the **Concepts & Synchronizations** model — independent modules connected through explicit sync rules. See `context/CONCEPTS.md` for the full conceptual model with 12 concepts and their synchronizations.

### Projects
A Project is a self-contained automation environment tied to a folder. Each project has its own database, cards, event queue, and file watchers. Projects are portable — zip and move.

### Cards
A Card is an automation: trigger + generated Python code + execution settings. Cards are stored in the project's SQLite database, programs in `.leaf/programs/`.

### Event Queue
All events (file changes, card executions, agent responses) flow through a central queue visible in the UI. WebSocket streams events to the frontend in real-time. Each project has its own queue.

### Interaction Primitives
The LLM can only use a fixed set of inputs/outputs (confirmation, choice, text_input, etc.) — no freeform UI generation. This keeps behavior predictable.

### Sandboxed Execution
Generated programs run via `uv run` in isolated environments. Each card has its own `pyproject.toml` and `uv.lock`. Programs can only write to the project folder.

## Environment Variables

```bash
PYDANTIC_AI_GATEWAY_API_KEY=xxx   # Required: AI Gateway key
LEAF_PORT=8000                     # Optional: API port
LEAF_MODEL=gateway/google:gemini-2.5-flash  # Optional: default model
LEAF_CONFIG_DIR=~/.leaf            # Optional: override app config location
```

## API Routes

### App-Level
- `GET /api/app/config` - Get app configuration
- `PUT /api/app/config` - Update app configuration
- `GET /api/projects` - List all known projects
- `POST /api/projects` - Create new project
- `POST /api/projects/open` - Open existing folder as project
- `DELETE /api/projects/{id}` - Remove from registry

### Project-Level (require active project)
- `GET /api/project` - Get current project info
- `GET /api/cards` - List cards
- `POST /api/cards` - Create card
- `GET /api/events` - List events
- `POST /api/chat` - Send chat message
- `WS /ws` - WebSocket for real-time events

## Implementation Status

**Phase 1: Foundation** - In progress
- FastAPI app skeleton with WebSocket support
- App-level config management (~/.leaf/)
- Project registry (projects.json CRUD)
- Project initialization (create .leaf/ folder structure)
- Per-project SQLite database setup with SQLModel
- Basic project switching

See `context/LEAF_SPEC.md` for full specification and `context/CONCEPTS.md` for the conceptual model.

## Important Files

- `context/LEAF_SPEC.md` — Full specification (v2.2) with architecture, schemas, and implementation phases
- `context/CONCEPTS.md` — Concepts & Synchronizations model (12 concepts, sync rules, example flows)
- `src/leaf/main.py` — FastAPI app entry point
- `src/leaf/projects/manager.py` — Project initialization and management
- `src/leaf/projects/registry.py` — projects.json management
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
