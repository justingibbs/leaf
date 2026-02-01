# LEAF - Claude Context

## What is LEAF?

LEAF (Local Event-Driven Automation Framework) is a desktop app that lets users create automations through natural language. Think "Claude Cowork meets HyperCard" — users describe what they want, an LLM generates Python code, and that code runs automatically when files are added to watched folders.

## Current Status

**Backend Complete (Phases 1-6)** — Ready for frontend development.

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Complete | Core infrastructure (FastAPI, config, projects) |
| 2 | ✅ Complete | File watcher with watchfiles |
| 3 | ✅ Complete | Cards & Triggers |
| 4 | ✅ Complete | PydanticAI Agent with streaming chat |
| 5 | ✅ Complete | Execution Engine (UV sandbox, retries) |
| 6 | ✅ Complete | MCP Integration |
| 7 | 🔲 Pending | Tauri + React Frontend |

## Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | Project overview and quick start |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, components, data flow |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Dev setup, testing, contributing |
| [docs/API.md](docs/API.md) | Complete REST API reference |
| [docs/CARDS.md](docs/CARDS.md) | Cards guide, triggers, programs |
| [docs/MCP.md](docs/MCP.md) | MCP integration guide |
| [context/LEAF_SPEC.md](context/LEAF_SPEC.md) | Original specification |

## Tech Stack

| Layer | Technology |
|-------|------------|
| Desktop Shell | Tauri 2.x (Phase 7) |
| Backend | FastAPI (Python) |
| Package Manager | UV |
| AI Framework | PydanticAI |
| Model Access | Pydantic AI Gateway (free Gemini) |
| Database | SQLite via SQLModel (per-project) |
| File Watching | watchfiles |
| Frontend | React + TypeScript (Phase 7) |

## Project Structure

```
leaf/
├── src/leaf/                  # Python backend
│   ├── main.py               # FastAPI entry point
│   ├── api/                  # REST & WebSocket routes
│   │   ├── app_routes.py     # App config
│   │   ├── project_routes.py # Projects, cards, chat
│   │   ├── execution_routes.py # Executions
│   │   ├── mcp_routes.py     # MCP servers
│   │   └── websocket.py      # WebSocket handlers
│   ├── agent/                # PydanticAI agent
│   │   ├── leaf_agent.py     # Agent + tools
│   │   ├── prompts.py        # System prompts
│   │   └── tools.py          # File operations
│   ├── cards/                # Card management
│   │   ├── registry.py       # CRUD operations
│   │   ├── models.py         # Pydantic models
│   │   └── matcher.py        # Event matching
│   ├── core/                 # Core infrastructure
│   │   ├── config.py         # Configuration
│   │   └── events.py         # Event bus
│   ├── db/                   # Database layer
│   │   ├── models.py         # SQLModel tables
│   │   └── session.py        # Session management
│   ├── execution/            # Execution engine
│   │   ├── sandbox.py        # UV sandbox
│   │   └── runner.py         # Orchestration + retries
│   ├── mcp/                  # MCP integration
│   │   ├── client.py         # MCP client
│   │   ├── config.py         # Server configuration
│   │   ├── registry.py       # Connection registry
│   │   └── card_helper.py    # Helper for cards
│   ├── projects/             # Project management
│   │   ├── manager.py        # Project CRUD
│   │   └── context.py        # Current project
│   └── watcher/              # File watching
│       └── file_watcher.py   # watchfiles integration
├── tests/                    # Test suite (112 tests)
├── docs/                     # Documentation
├── context/                  # Specs and concepts
├── pyproject.toml
└── .env.example
```

## Key Commands

```bash
# Setup
uv sync                       # Install dependencies
cp .env.example .env          # Configure environment

# Development
uv run python -m leaf.main    # Start backend (port 8000)

# Testing
uv run pytest                 # Run all tests (112 tests)
uv run pytest -v              # Verbose output
uv run ruff check .           # Lint
```

## Environment Variables

```bash
PYDANTIC_AI_API_KEY=xxx       # Required: Pydantic AI Gateway key
LEAF_MODEL=google-gla:gemini-2.0-flash  # Optional: AI model
LEAF_PORT=8000                # Optional: API port
LEAF_CONFIG_DIR=~/.config/leaf # Optional: config location
```

## API Overview

The backend runs at `http://127.0.0.1:8000`.

### Projects
- `POST /api/projects` - Create project
- `GET /api/projects` - List projects
- `POST /api/projects/switch` - Switch to project
- `GET /api/projects/current` - Get current project

### Cards
- `POST /api/cards` - Create card
- `GET /api/cards` - List cards
- `GET /api/cards/{id}` - Get card
- `PATCH /api/cards/{id}` - Update card
- `DELETE /api/cards/{id}` - Delete card
- `POST /api/cards/{id}/trigger` - Manual trigger

### Chat
- `POST /api/chat` - Send message to agent
- `GET /api/chat/history` - Get chat history
- `WS /ws/chat` - Streaming chat

### Executions
- `GET /api/executions` - List executions
- `GET /api/executions/{id}` - Get execution
- `POST /api/executions/manual` - Execute card manually

### MCP
- `GET /api/mcp/servers` - List MCP servers
- `POST /api/mcp/servers` - Add server
- `POST /api/mcp/servers/{id}/connect` - Connect to server
- `GET /api/mcp/tools` - List available tools
- `POST /api/mcp/tools/call` - Call a tool

### WebSocket
- `WS /ws` - Real-time events (file changes, executions)
- `WS /ws/chat` - Streaming chat responses

See [docs/API.md](docs/API.md) for complete reference.

## Core Concepts

### Projects
A folder with `.leaf/` containing database, card programs, and config. Each project is self-contained and portable.

### Cards
An automation unit: trigger + Python program + settings. Created via AI agent or API.

**Trigger Types:**
- `file_created` - File added to watched folder
- `file_modified` - File changed
- `manual` - API triggered
- `schedule` - Cron-based (future)

### Execution
Cards run in isolated UV virtual environments with:
- Configurable timeout (default: 5 min)
- Automatic retries (default: 3)
- stdout/stderr capture
- Environment variables (`LEAF_PROJECT_ROOT`, `LEAF_CARD_ID`)

### MCP Integration
Connect to MCP servers for external tools. Built-in servers: filesystem, fetch, memory.

## Phase 7: Frontend

The frontend needs to implement:

1. **Tauri** desktop wrapper
2. **React + TypeScript** UI
3. **Views:**
   - Project selector/manager
   - Cards dashboard
   - Card detail/editor
   - Chat interface (streaming)
   - Execution history
   - MCP server management
   - Real-time event feed

4. **WebSocket Integration:**
   - `/ws` for live events
   - `/ws/chat` for streaming responses

## Code Style

- Python 3.11+
- Type hints required
- Async everywhere
- Pydantic models for data
- Ruff for linting
- pytest for testing
