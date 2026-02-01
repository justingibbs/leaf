# LEAF - Local Event-Driven Automation Framework

LEAF is a desktop application that enables event-driven automations through natural language. Describe what you want to automate, and LEAF's AI agent creates the automation for you.

## Features

- **Natural Language Automation**: Describe automations in plain English - LEAF's AI agent generates the code
- **Event-Driven Triggers**: Automate based on file changes, schedules, or manual triggers
- **Sandboxed Execution**: Each automation runs in an isolated UV-managed Python environment
- **MCP Integration**: Connect to external tools via the Model Context Protocol
- **Project-Based**: Organize automations by project with isolated databases
- **Real-Time Monitoring**: WebSocket-based event streaming and execution tracking

## Quick Start

### Prerequisites

- Python 3.11+
- [UV](https://docs.astral.sh/uv/) package manager
- Node.js (for MCP servers, optional)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/leaf.git
cd leaf

# Install dependencies with UV
uv sync

# Copy environment template and configure
cp .env.example .env
# Edit .env with your API key
```

### Configuration

Create a `.env` file with your Pydantic AI Gateway key:

```bash
PYDANTIC_AI_API_KEY=your-pydantic-ai-gateway-key-here
LEAF_MODEL=google-gla:gemini-2.0-flash
```

Get a free API key from [Pydantic AI Gateway](https://ai.pydantic.dev/).

### Running LEAF

```bash
# Start the server
uv run python -m leaf.main

# Or use the CLI entry point
uv run leaf
```

The API server starts at `http://127.0.0.1:8000`.

## Usage Example

### 1. Create a Project

```bash
curl -X POST http://127.0.0.1:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/my/project", "name": "My Automation Project"}'
```

### 2. Switch to the Project

```bash
curl -X POST http://127.0.0.1:8000/api/projects/switch \
  -H "Content-Type: application/json" \
  -d '{"project_id": "proj_xxxxx"}'
```

### 3. Chat with the Agent

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"content": "Create an automation that processes CSV files in the inbox folder and generates a summary report"}'
```

The agent will propose a Card (automation) and create it upon confirmation.

### 4. Watch It Work

Drop a CSV file into your project's `inbox/` folder. LEAF detects it, triggers the card, and executes your automation.

## Core Concepts

### Cards

A **Card** is an automation unit consisting of:
- **Trigger**: What starts the automation (file change, schedule, manual)
- **Program**: Python code that runs when triggered
- **Configuration**: Timeout, retries, dependencies

### Projects

Each project has:
- Its own SQLite database (`.leaf/leaf.db`)
- Card programs directory (`.leaf/programs/`)
- Isolated file watching

### Events

LEAF is event-driven. Events flow through the system:
1. File watcher detects a change
2. Event is emitted and persisted
3. Matching cards are found
4. Cards execute in sandboxed environments
5. Results are stored and broadcast via WebSocket

## Project Structure

```
leaf/
├── src/leaf/
│   ├── agent/          # PydanticAI agent and tools
│   ├── api/            # FastAPI routes
│   ├── cards/          # Card management
│   ├── core/           # Configuration and events
│   ├── db/             # Database models and sessions
│   ├── execution/      # Sandbox execution engine
│   ├── mcp/            # MCP client integration
│   ├── projects/       # Project management
│   └── watcher/        # File system watcher
├── tests/              # Test suite
├── docs/               # Documentation
└── pyproject.toml
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design and components
- [Development](docs/DEVELOPMENT.md) - Development setup and contributing
- [API Reference](docs/API.md) - REST and WebSocket API
- [Cards Guide](docs/CARDS.md) - Creating and managing automations
- [MCP Integration](docs/MCP.md) - External tool integration

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific phase tests
uv run pytest tests/test_phase3.py -v
```

## License

MIT

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- AI powered by [PydanticAI](https://ai.pydantic.dev/)
- Package management by [UV](https://docs.astral.sh/uv/)
- Protocol support via [MCP](https://modelcontextprotocol.io/)
