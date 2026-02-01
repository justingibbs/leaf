# LEAF - Local Event-Driven Automation Framework

## Specification v2.0

---

## Overview

LEAF is a local-first desktop application that enables users to create event-driven automations through natural language. Inspired by HyperCard's approachability and Claude Cowork's sandboxed agent model, LEAF provides a constrained, predictable environment where an LLM can observe, reason, write code, and act on files within a user-defined workspace.

### Core Workflow

1. User opens LEAF and selects a folder to share
2. User describes what they want: *"Analyze CSV files dropped here and generate a summary report"*
3. LEAF's agent creates a **Card** and writes Python code to perform the analysis
4. When files are added to the watched folder, the Card triggers automatically
5. The analysis runs, a report is generated, and everything is visible in the **Event Queue**

### Core Principles

1. **Fully Local** — No cloud sync, no external services except LLM API calls and MCP servers
2. **Sandboxed** — All code execution and file writes confined to the user-designated workspace
3. **Event-Driven** — Cards react to file system events, schedules, or manual triggers
4. **Code-Generating** — The LLM writes Python programs to accomplish user goals
5. **Typed Interactions** — LLM operates within a fixed vocabulary of inputs, outputs, and actions
6. **Transparent** — All events, executions, and agent reasoning visible in a real-time queue

---

## Technology Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| Desktop Shell | Tauri 2.x | Rust backend, WebView frontend, ~5MB bundle |
| Backend | FastAPI | Async Python, WebSocket support |
| Package Manager | UV | Fast, Rust-based, replaces pip/venv/pyenv |
| AI Framework | PydanticAI | Agents, structured outputs, MCP integration |
| Model Access | Pydantic AI Gateway | Multi-provider, cost control, native format passthrough |
| Workflow Engine | Temporal | Durable execution, crash recovery, retries |
| Database | SQLite via SQLModel | Local persistence, Pydantic-native |
| File Watching | watchfiles | Rust-based, fast, cross-platform |
| UI Framework | React + TypeScript | Tauri frontend |
| Styling | Tailwind CSS | Rapid iteration |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Tauri Shell (macOS)                       │
│   • Window management                                            │
│   • System tray                                                  │
│   • Native file dialogs                                          │
│   • Notifications                                                │
└─────────────────────────────┬───────────────────────────────────┘
                              │ localhost:8000 (HTTP + WebSocket)
┌─────────────────────────────▼───────────────────────────────────┐
│                      FastAPI Application                         │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    API Routes                               │ │
│  │  /api/workspace    /api/cards    /api/events    /api/chat  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  WebSocket Manager                          │ │
│  │              (real-time event streaming)                    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌───────────────┬──────────────────┬────────────────────────┐ │
│  │               │                  │                        │ │
│  ▼               ▼                  ▼                        ▼ │
│ ┌─────────┐ ┌──────────────┐ ┌─────────────┐ ┌─────────────┐  │
│ │Workspace│ │ File Watcher │ │    Card     │ │  Chat/Agent │  │
│ │ Manager │ │ (watchfiles) │ │  Registry   │ │  Interface  │  │
│ └────┬────┘ └──────┬───────┘ └──────┬──────┘ └──────┬──────┘  │
│      │             │                │               │          │
│      └─────────────┴────────────────┴───────────────┘          │
│                              │                                  │
│  ┌───────────────────────────▼────────────────────────────────┐ │
│  │                     Event Bus                               │ │
│  │                  (asyncio Queue)                            │ │
│  └───────────────────────────┬────────────────────────────────┘ │
│                              │                                  │
│  ┌───────────────────────────▼────────────────────────────────┐ │
│  │                  Temporal Worker                            │ │
│  │                                                             │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │              Card Execution Workflow                 │   │ │
│  │  │                                                      │   │ │
│  │  │  1. Receive event                                    │   │ │
│  │  │  2. Load card + generated code                       │   │ │
│  │  │  3. Execute in sandbox                               │   │ │
│  │  │  4. Capture outputs                                  │   │ │
│  │  │  5. Update card state                                │   │ │
│  │  │  6. Emit completion event                            │   │ │
│  │  └─────────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    PydanticAI Agent                         │ │
│  │                                                             │ │
│  │  • Card creation from natural language                      │ │
│  │  • Python code generation                                   │ │
│  │  • Interaction handling (confirmations, choices)            │ │
│  │  • MCP tool access                                          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Sandbox Executor                         │ │
│  │                                                             │ │
│  │  • Isolated Python environment (UV-managed)                 │ │
│  │  • Restricted to workspace folder                           │ │
│  │  • Timeout enforcement                                      │ │
│  │  • Output capture (stdout, files created)                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    MCP Client Manager                       │ │
│  │                                                             │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │ │
│  │  │  Postgres   │  │   GitHub    │  │   Custom    │        │ │
│  │  │   Server    │  │   Server    │  │   Server    │        │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   SQLite Database                           │ │
│  │   workspaces │ cards │ events │ executions │ mcp_servers   │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                    Temporal Server (embedded)                     │
│                                                                   │
│   • Workflow persistence                                          │
│   • Automatic retries                                             │
│   • Crash recovery                                                │
│   • Execution history                                             │
└──────────────────────────────────────────────────────────────────┘
```

---

## Workspace Model

### Folder Structure

When a user designates a workspace folder, LEAF creates:

```
~/Documents/MyWorkspace/          # User-designated root
├── .leaf/                        # LEAF system folder
│   ├── config.json               # Workspace configuration
│   ├── cards/                    # Card definitions (JSON)
│   │   ├── csv-analyzer.json
│   │   └── image-resizer.json
│   ├── programs/                 # Generated Python programs
│   │   ├── csv-analyzer/
│   │   │   ├── main.py
│   │   │   └── pyproject.toml    # UV manages dependencies
│   │   └── image-resizer/
│   │       ├── main.py
│   │       └── pyproject.toml
│   ├── logs/                     # Execution logs
│   ├── outputs/                  # Generated reports/outputs
│   └── leaf.db                   # SQLite database
├── inbox/                        # Example: watched folder
├── reports/                      # Example: output folder
└── ...                           # User's other folders and files
```

### Permissions Model

| Location | Read | Write | Execute |
|----------|------|-------|---------|
| Inside workspace (excluding .leaf/) | ✅ | ✅ | ❌ |
| .leaf/programs/ | ✅ | ✅ (LEAF only) | ✅ (sandboxed) |
| .leaf/outputs/ | ✅ | ✅ | ❌ |
| .leaf/ (other) | ✅ | ✅ (LEAF only) | ❌ |
| Outside workspace | ✅ (with permission) | ❌ | ❌ |

---

## Card Model

A Card represents a complete automation: the trigger, the code, and the expected behavior.

### Card Definition Schema

```python
from pydantic import BaseModel
from typing import Literal
from datetime import datetime

class TriggerConfig(BaseModel):
    type: Literal["file_created", "file_modified", "schedule", "manual"]
    folder: str | None = None          # Relative to workspace
    pattern: str | None = None         # Glob pattern, e.g., "*.csv"
    cron: str | None = None            # For schedule triggers

class GeneratedProgram(BaseModel):
    language: Literal["python"] = "python"
    entrypoint: str = "main.py"        # Relative to program folder
    dependencies: list[str] = []       # pip packages

class Card(BaseModel):
    id: str
    name: str
    description: str

    # What the user originally asked for
    user_prompt: str

    # Trigger configuration
    trigger: TriggerConfig

    # Generated program
    program: GeneratedProgram
    program_path: str                  # e.g., ".leaf/programs/csv-analyzer"

    # Execution settings
    timeout_seconds: int = 300
    retry_count: int = 3
    enabled: bool = True

    # Allowed interactions (AG-UI style constraints)
    allowed_outputs: list[str] = ["message", "progress", "file_created"]

    # Metadata
    created_at: datetime
    updated_at: datetime
    last_run_at: datetime | None = None
    run_count: int = 0
```

### Example Card

```json
{
  "id": "card_abc123",
  "name": "CSV Analyzer",
  "description": "Analyzes CSV files and generates summary reports",
  "user_prompt": "When a CSV file is added to the inbox folder, analyze it and create a summary report with row count, column stats, and any anomalies",
  "trigger": {
    "type": "file_created",
    "folder": "inbox",
    "pattern": "*.csv"
  },
  "program": {
    "language": "python",
    "entrypoint": "main.py",
    "dependencies": ["pandas", "numpy"]
  },
  "program_path": ".leaf/programs/csv-analyzer",
  "timeout_seconds": 300,
  "retry_count": 3,
  "enabled": true,
  "allowed_outputs": ["message", "progress", "file_created"],
  "created_at": "2025-01-31T10:00:00Z",
  "updated_at": "2025-01-31T10:00:00Z",
  "last_run_at": null,
  "run_count": 0
}
```

### Generated Program Example

`.leaf/programs/csv-analyzer/main.py`:

```python
#!/usr/bin/env python3
"""
CSV Analyzer - Generated by LEAF
Analyzes CSV files and generates summary reports.
"""
import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

def analyze(input_file: Path, output_dir: Path) -> dict:
    """Analyze a CSV file and return summary statistics."""
    df = pd.read_csv(input_file)

    summary = {
        "file": input_file.name,
        "analyzed_at": datetime.now().isoformat(),
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": {},
        "anomalies": []
    }

    for col in df.columns:
        col_stats = {
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].isnull().sum()),
            "unique_count": int(df[col].nunique())
        }
        if df[col].dtype in ['int64', 'float64']:
            col_stats.update({
                "mean": float(df[col].mean()),
                "min": float(df[col].min()),
                "max": float(df[col].max())
            })
        summary["columns"][col] = col_stats

    # Detect anomalies
    null_threshold = len(df) * 0.5
    for col, stats in summary["columns"].items():
        if stats["null_count"] > null_threshold:
            summary["anomalies"].append(f"Column '{col}' has >50% null values")

    # Write report
    report_name = f"report_{input_file.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path = output_dir / report_name
    report_path.write_text(json.dumps(summary, indent=2))

    return {
        "status": "success",
        "report_path": str(report_path),
        "summary": f"Analyzed {summary['row_count']} rows, {summary['column_count']} columns"
    }

if __name__ == "__main__":
    # LEAF passes: input_file, workspace_root, output_dir
    input_file = Path(sys.argv[1])
    workspace_root = Path(sys.argv[2])
    output_dir = Path(sys.argv[3])

    result = analyze(input_file, output_dir)

    # Output JSON for LEAF to capture
    print(json.dumps(result))
```

---

## Event System

### Event Types

| Type | Payload | Description |
|------|---------|-------------|
| `file.created` | `{path, folder, filename, size}` | New file detected |
| `file.modified` | `{path, folder, filename, size}` | File changed |
| `file.deleted` | `{path, folder, filename}` | File removed |
| `schedule.triggered` | `{cron, scheduled_time}` | Cron schedule fired |
| `card.triggered` | `{card_id, trigger_event_id}` | Card execution started |
| `card.completed` | `{card_id, execution_id, result}` | Card execution finished |
| `card.failed` | `{card_id, execution_id, error}` | Card execution failed |
| `user.chat` | `{message}` | User sent chat message |
| `agent.response` | `{message, card_id?}` | Agent responded |

### Event Schema

```python
from pydantic import BaseModel
from typing import Literal, Any
from datetime import datetime

class Event(BaseModel):
    id: str
    type: str
    timestamp: datetime
    payload: dict[str, Any]

    # Processing state
    status: Literal["pending", "processing", "completed", "failed"] = "pending"
    matched_cards: list[str] = []

    # If this event triggered an execution
    execution_id: str | None = None

    # Parent event (for card.completed -> file.created chain)
    parent_event_id: str | None = None
```

### Event Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  File System                                                     │
│  ~/workspace/inbox/data.csv (created)                           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  File Watcher (watchfiles)                                       │
│  Detects: CREATE inbox/data.csv                                  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Event Bus                                                       │
│  Event: {type: "file.created", path: "inbox/data.csv", ...}     │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Card Matcher                                                    │
│  Matches: CSV Analyzer card (pattern: "*.csv", folder: "inbox") │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Temporal Workflow                                               │
│  Starts: CardExecutionWorkflow(card_id, event)                  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Sandbox Executor                                                │
│  Runs: python main.py "inbox/data.csv" "/workspace" "/outputs"  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Event Bus                                                       │
│  Event: {type: "card.completed", result: {...}}                 │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  WebSocket                                                       │
│  Broadcasts to UI → Event Queue updates in real-time            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Temporal Integration

### Workflow Definition

```python
from temporalio import workflow, activity
from temporalio.common import RetryPolicy
from datetime import timedelta

@activity.defn
async def setup_sandbox(card_id: str) -> str:
    """Ensure UV environment exists with required dependencies."""
    # Uses `uv sync` to install dependencies
    # Returns path to program directory (UV runs via `uv run`)
    ...

@activity.defn
async def execute_program(
    program_path: str,
    input_file: str,
    workspace_root: str,
    output_dir: str,
    timeout: int
) -> dict:
    """Run the generated program in sandbox using UV."""
    import asyncio
    import subprocess

    # UV handles the virtual environment automatically
    proc = await asyncio.create_subprocess_exec(
        "uv", "run", "main.py", input_file, workspace_root, output_dir,
        cwd=program_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout
        )
        return {
            "exit_code": proc.returncode,
            "stdout": stdout.decode(),
            "stderr": stderr.decode()
        }
    except asyncio.TimeoutError:
        proc.kill()
        raise TimeoutError(f"Program exceeded {timeout}s timeout")

@activity.defn
async def update_card_state(card_id: str, execution_result: dict) -> None:
    """Update card with execution results."""
    ...

@activity.defn
async def emit_event(event_type: str, payload: dict) -> None:
    """Emit event to the event bus."""
    ...

@workflow.defn
class CardExecutionWorkflow:
    @workflow.run
    async def run(self, card_id: str, trigger_event: dict) -> dict:
        # Load card
        card = await workflow.execute_activity(
            load_card,
            card_id,
            start_to_close_timeout=timedelta(seconds=10)
        )

        # Emit started event
        await workflow.execute_activity(
            emit_event,
            args=["card.triggered", {"card_id": card_id}],
            start_to_close_timeout=timedelta(seconds=5)
        )

        # Setup sandbox (uv sync to install dependencies)
        await workflow.execute_activity(
            setup_sandbox,
            card_id,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=3)
        )

        # Execute the program (UV handles the environment)
        try:
            result = await workflow.execute_activity(
                execute_program,
                args=[
                    card["program_path"],
                    trigger_event["payload"]["path"],
                    card["workspace_root"],
                    card["output_dir"],
                    card["timeout_seconds"]
                ],
                start_to_close_timeout=timedelta(seconds=card["timeout_seconds"] + 30),
                retry_policy=RetryPolicy(maximum_attempts=card["retry_count"])
            )

            # Emit completed event
            await workflow.execute_activity(
                emit_event,
                args=["card.completed", {"card_id": card_id, "result": result}],
                start_to_close_timeout=timedelta(seconds=5)
            )

            return result

        except Exception as e:
            # Emit failed event
            await workflow.execute_activity(
                emit_event,
                args=["card.failed", {"card_id": card_id, "error": str(e)}],
                start_to_close_timeout=timedelta(seconds=5)
            )
            raise
```

### Temporal Setup

LEAF runs an embedded Temporal server for local development:

```python
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

async def start_temporal():
    # Start embedded Temporal server
    env = await WorkflowEnvironment.start_local()

    # Create worker
    worker = Worker(
        env.client,
        task_queue="leaf-cards",
        workflows=[CardExecutionWorkflow],
        activities=[
            setup_sandbox,
            execute_program,
            update_card_state,
            emit_event,
            load_card
        ]
    )

    return env, worker
```

For production, users can optionally connect to an external Temporal server.

---

## UV Integration

UV powers both the main LEAF application and the sandboxed execution of generated programs.

### Main Application

```bash
# Project initialization
uv init leaf
cd leaf
uv add fastapi uvicorn pydantic-ai sqlmodel watchfiles temporalio

# Running the app
uv run uvicorn leaf.main:app --reload

# The uv.lock file is committed for reproducible builds
```

### Generated Program Sandboxes

Each Card's generated program gets its own UV project:

```
.leaf/programs/csv-analyzer/
├── main.py           # Generated code
├── pyproject.toml    # UV project config
└── uv.lock           # Locked dependencies (auto-generated)
```

**pyproject.toml** (auto-generated):
```toml
[project]
name = "csv-analyzer"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pandas>=2.0.0",
    "numpy>=1.24.0",
]
```

### Sandbox Setup Activity

```python
@activity.defn
async def setup_sandbox(card_id: str) -> None:
    """Install dependencies for a card's program using UV."""
    card = await load_card(card_id)
    program_path = Path(card.program_path)

    # UV sync installs dependencies and creates .venv automatically
    proc = await asyncio.create_subprocess_exec(
        "uv", "sync",
        cwd=program_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"Failed to sync dependencies for card {card_id}")
```

### Execution via UV

```python
# UV handles the virtual environment automatically
proc = await asyncio.create_subprocess_exec(
    "uv", "run", "main.py", input_file, workspace_root, output_dir,
    cwd=program_path,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)
```

### Benefits of UV for LEAF

| Benefit | Impact |
|---------|--------|
| **Speed** | 10-100x faster than pip for dependency resolution |
| **Isolation** | Each card gets its own locked environment |
| **Reproducibility** | Lockfiles ensure consistent execution |
| **No Python management** | UV handles Python versions if needed |
| **Disk efficiency** | Global cache shared across all card environments |
| **Single tool** | No need for venv, pip, pip-tools separately |

---

## PydanticAI Agent

### Agent Configuration

```python
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

# Structured outputs for card creation
class CardCreationResult(BaseModel):
    card_name: str
    card_description: str
    trigger_type: str
    trigger_folder: str | None
    trigger_pattern: str | None
    program_code: str
    dependencies: list[str]
    explanation: str

# The main LEAF agent
leaf_agent = Agent(
    'gateway/google:gemini-2.5-flash',
    result_type=CardCreationResult,
    system_prompt="""
You are LEAF, a local automation assistant. Users describe automations they want,
and you create Cards with Python programs to accomplish their goals.

WORKSPACE: {workspace_path}

When creating a program:
1. Write clean, focused Python code
2. Use the standard interface: main.py receives (input_file, workspace_root, output_dir)
3. Output results as JSON to stdout
4. Handle errors gracefully
5. Only use packages from PyPI that you specify in dependencies

Available trigger types:
- file_created: Fires when a new file appears in a folder
- file_modified: Fires when a file changes
- schedule: Fires on a cron schedule
- manual: User clicks "Run"
"""
)
```

### Card Creation Flow

```python
async def create_card_from_prompt(user_prompt: str, workspace: Workspace) -> Card:
    """Create a new card from a user's natural language request."""

    result = await leaf_agent.run(
        user_prompt,
        context={"workspace_path": str(workspace.path)}
    )

    # Create card
    card = Card(
        id=generate_id(),
        name=result.data.card_name,
        description=result.data.card_description,
        user_prompt=user_prompt,
        trigger=TriggerConfig(
            type=result.data.trigger_type,
            folder=result.data.trigger_folder,
            pattern=result.data.trigger_pattern
        ),
        program=GeneratedProgram(
            dependencies=result.data.dependencies
        ),
        program_path=f".leaf/programs/{slugify(result.data.card_name)}"
    )

    # Write program files
    program_dir = workspace.path / card.program_path
    program_dir.mkdir(parents=True, exist_ok=True)
    (program_dir / "main.py").write_text(result.data.program_code)

    # Create pyproject.toml for UV
    pyproject = f"""[project]
name = "{slugify(result.data.card_name)}"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = {result.data.dependencies!r}
"""
    (program_dir / "pyproject.toml").write_text(pyproject)

    # Save card
    await save_card(card)

    # Register trigger with file watcher
    await register_trigger(card)

    return card
```

---

## Interaction Primitives

LEAF constrains LLM interactions to a fixed set of primitives, inspired by AG-UI.

### Input Primitives (Agent requests from user)

```python
from pydantic import BaseModel
from typing import Literal

class Confirmation(BaseModel):
    type: Literal["confirmation"] = "confirmation"
    message: str
    confirm_label: str = "Yes"
    cancel_label: str = "No"

class TextInput(BaseModel):
    type: Literal["text_input"] = "text_input"
    message: str
    placeholder: str = ""
    default: str = ""

class Choice(BaseModel):
    type: Literal["choice"] = "choice"
    message: str
    options: list[dict]  # [{id: str, label: str}]

class FileSelect(BaseModel):
    type: Literal["file_select"] = "file_select"
    message: str
    folder: str | None = None
    pattern: str = "*"
    multiple: bool = False

InteractionRequest = Confirmation | TextInput | Choice | FileSelect
```

### Output Primitives (Agent displays to user)

```python
class Message(BaseModel):
    type: Literal["message"] = "message"
    content: str
    level: Literal["info", "success", "warning", "error"] = "info"

class Progress(BaseModel):
    type: Literal["progress"] = "progress"
    message: str
    current: int | None = None
    total: int | None = None

class CodePreview(BaseModel):
    type: Literal["code_preview"] = "code_preview"
    title: str
    code: str
    language: str = "python"

class FileCreated(BaseModel):
    type: Literal["file_created"] = "file_created"
    path: str
    description: str

OutputEvent = Message | Progress | CodePreview | FileCreated
```

### Agent Response Schema

```python
class AgentResponse(BaseModel):
    """All agent responses must conform to this schema."""
    thinking: str  # Brief reasoning (shown in UI as collapsed)

    response_type: Literal[
        "message",       # Display information
        "interaction",   # Request user input
        "card_created",  # New card was created
        "executing",     # Running a card
        "complete"       # Done with current task
    ]

    # One of these based on response_type
    output: OutputEvent | None = None
    interaction: InteractionRequest | None = None
    card: Card | None = None
```

---

## User Interface

### Main Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  LEAF                                      ~/Documents/MyWorkspace  [⚙] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                          CHAT PANEL                                 │ │
│  │                                                                     │ │
│  │  You: When a CSV file is added to inbox/, analyze it and create    │ │
│  │       a summary report                                              │ │
│  │                                                                     │ │
│  │  LEAF: I'll create a Card for that. Here's what I'm planning:      │ │
│  │                                                                     │ │
│  │  ┌─────────────────────────────────────────────────────────────┐   │ │
│  │  │  📊 CSV Analyzer                                             │   │ │
│  │  │  Trigger: New *.csv files in inbox/                         │   │ │
│  │  │  Action: Analyze with pandas, generate JSON report          │   │ │
│  │  │                                                              │   │ │
│  │  │  [View Code]  [Create Card]  [Modify]                       │   │ │
│  │  └─────────────────────────────────────────────────────────────┘   │ │
│  │                                                                     │ │
│  │  ┌─────────────────────────────────────────────────────────────┐   │ │
│  │  │ Ask LEAF anything...                                    [↵] │   │ │
│  │  └─────────────────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
├──────────────────────┬───────────────────────────────────────────────────┤
│                      │                                                   │
│   CARDS              │              EVENT QUEUE                          │
│   ─────              │   ─────────────────────────────────────────────   │
│                      │                                                   │
│   ┌────────────────┐ │   ┌──────────────────────────────────────────┐   │
│   │ 📊 CSV Analyzer│ │   │ 10:32:15  file.created  inbox/sales.csv  │   │
│   │    ● Active    │ │   │           → CSV Analyzer                  │   │
│   │    Runs: 12    │ │   │           ⟳ Processing...                │   │
│   └────────────────┘ │   ├──────────────────────────────────────────┤   │
│                      │   │ 10:31:42  card.completed  CSV Analyzer   │   │
│   ┌────────────────┐ │   │           ✓ report_data_20250131.json    │   │
│   │ 🖼 Image Resize│ │   ├──────────────────────────────────────────┤   │
│   │    ● Active    │ │   │ 10:31:40  file.created  inbox/data.csv   │   │
│   │    Runs: 5     │ │   │           → CSV Analyzer                  │   │
│   └────────────────┘ │   │           ✓ Completed (2.3s)             │   │
│                      │   ├──────────────────────────────────────────┤   │
│   [+ New Card]       │   │ 10:30:00  schedule.triggered             │   │
│                      │   │           → Daily Backup                  │   │
│                      │   │           ✓ Completed                     │   │
│                      │   └──────────────────────────────────────────┘   │
│                      │                                                   │
└──────────────────────┴───────────────────────────────────────────────────┘
```

### Card Detail View

When a card is selected:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  CSV Analyzer                                            [Edit] [Delete] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  TRIGGER                                                                 │
│  ──────────────────────────────────────────────────────────────────     │
│  When: New file created                                                  │
│  Folder: inbox/                                                          │
│  Pattern: *.csv                                                          │
│  Status: ● Watching                                                      │
│                                                                          │
│  PROGRAM                                                                 │
│  ──────────────────────────────────────────────────────────────────     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ main.py                                                             │ │
│  │ ─────────────────────────────────────────────────────────────────  │ │
│  │ import pandas as pd                                                 │ │
│  │ from pathlib import Path                                            │ │
│  │ ...                                                                 │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│  Dependencies: pandas, numpy                                             │
│                                                                          │
│  RECENT EXECUTIONS                                                       │
│  ──────────────────────────────────────────────────────────────────     │
│  │ 10:31:40  sales.csv     ✓ 2.3s   report_sales_20250131.json       │ │
│  │ 10:15:22  inventory.csv ✓ 1.8s   report_inventory_20250131.json   │ │
│  │ 09:45:00  orders.csv    ✗ Error  "Column 'date' not found"        │ │
│                                                                          │
│  [Run Manually]  [View All Executions]                                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## MCP Integration

### Configuration

```json
// .leaf/config.json
{
  "workspace_path": "/Users/me/Documents/MyWorkspace",
  "mcp_servers": [
    {
      "id": "postgres-main",
      "name": "Main Database",
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"]
    },
    {
      "id": "github",
      "name": "GitHub",
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    }
  ]
}
```

### Agent with MCP Tools

```python
from pydantic_ai.mcp import MCPServerStdio

async def create_agent_with_mcp(config: WorkspaceConfig) -> Agent:
    mcp_servers = []

    for server_config in config.mcp_servers:
        server = MCPServerStdio(
            server_config.command,
            server_config.args
        )
        mcp_servers.append(server)

    return Agent(
        'gateway/google:gemini-2.5-flash',
        mcp_servers=mcp_servers,
        system_prompt=LEAF_SYSTEM_PROMPT
    )
```

### MCP-Enhanced Cards

With MCP, cards can access external data:

```
User: "Every morning at 9am, check the orders table for orders placed
       yesterday and create a summary report"

LEAF creates a card with:
- Trigger: schedule (cron: "0 9 * * *")
- Program that uses MCP postgres server to query orders table
- Generates report in outputs/
```

---

## Database Schema

```sql
-- Workspace
CREATE TABLE workspaces (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Cards
CREATE TABLE cards (
    id TEXT PRIMARY KEY,
    workspace_id TEXT REFERENCES workspaces(id),
    name TEXT NOT NULL,
    description TEXT,
    user_prompt TEXT NOT NULL,
    trigger_config TEXT NOT NULL,  -- JSON
    program_config TEXT NOT NULL,  -- JSON
    program_path TEXT NOT NULL,
    timeout_seconds INTEGER DEFAULT 300,
    retry_count INTEGER DEFAULT 3,
    enabled BOOLEAN DEFAULT TRUE,
    allowed_outputs TEXT NOT NULL,  -- JSON array
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_run_at DATETIME,
    run_count INTEGER DEFAULT 0
);

-- Events
CREATE TABLE events (
    id TEXT PRIMARY KEY,
    workspace_id TEXT REFERENCES workspaces(id),
    type TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    payload TEXT NOT NULL,  -- JSON
    status TEXT DEFAULT 'pending',
    matched_cards TEXT,  -- JSON array of card IDs
    execution_id TEXT,
    parent_event_id TEXT REFERENCES events(id)
);

-- Executions (card runs)
CREATE TABLE executions (
    id TEXT PRIMARY KEY,
    card_id TEXT REFERENCES cards(id),
    event_id TEXT REFERENCES events(id),
    status TEXT NOT NULL,  -- pending, running, completed, failed
    started_at DATETIME,
    completed_at DATETIME,
    result TEXT,  -- JSON
    error TEXT,
    stdout TEXT,
    stderr TEXT
);

-- MCP Server configurations
CREATE TABLE mcp_servers (
    id TEXT PRIMARY KEY,
    workspace_id TEXT REFERENCES workspaces(id),
    name TEXT NOT NULL,
    type TEXT NOT NULL,  -- stdio, http
    command TEXT,
    args TEXT,  -- JSON array
    url TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Chat history
CREATE TABLE chat_messages (
    id TEXT PRIMARY KEY,
    workspace_id TEXT REFERENCES workspaces(id),
    role TEXT NOT NULL,  -- user, assistant
    content TEXT NOT NULL,
    metadata TEXT,  -- JSON (card_id if card was created, etc.)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_events_workspace ON events(workspace_id);
CREATE INDEX idx_events_type ON events(type);
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_executions_card ON executions(card_id);
CREATE INDEX idx_executions_status ON executions(status);
```

---

## Project Structure

```
leaf/
├── tauri/                          # Tauri shell
│   ├── src/
│   │   └── main.rs                 # Window management, system tray
│   ├── tauri.conf.json
│   └── Cargo.toml
│
├── frontend/                       # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatPanel.tsx
│   │   │   ├── CardList.tsx
│   │   │   ├── CardDetail.tsx
│   │   │   ├── EventQueue.tsx
│   │   │   └── Settings.tsx
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts
│   │   │   └── useCards.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── src/
│   └── leaf/
│       ├── __init__.py
│       ├── main.py                 # FastAPI app entry
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── routes.py           # API routes
│       │   └── websocket.py        # WebSocket handler
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py           # Settings, environment
│       │   └── events.py           # Event bus
│       │
│       ├── workspace/
│       │   ├── __init__.py
│       │   ├── manager.py          # Workspace operations
│       │   └── watcher.py          # File watching
│       │
│       ├── cards/
│       │   ├── __init__.py
│       │   ├── models.py           # Card, Trigger schemas
│       │   ├── registry.py         # Card CRUD
│       │   └── matcher.py          # Event → Card matching
│       │
│       ├── execution/
│       │   ├── __init__.py
│       │   ├── sandbox.py          # Sandboxed execution
│       │   └── workflows.py        # Temporal workflows
│       │
│       ├── agent/
│       │   ├── __init__.py
│       │   ├── leaf_agent.py       # PydanticAI agent
│       │   ├── prompts.py          # System prompts
│       │   └── primitives.py       # Interaction types
│       │
│       ├── mcp/
│       │   ├── __init__.py
│       │   └── client.py           # MCP server management
│       │
│       └── db/
│           ├── __init__.py
│           ├── models.py           # SQLModel schemas
│           └── session.py          # Database session
│
├── tests/
│   ├── test_cards.py
│   ├── test_execution.py
│   └── test_agent.py
│
├── pyproject.toml                  # UV project config
├── uv.lock                         # UV lockfile (committed)
└── README.md
```

---

## Implementation Phases

### Phase 1: Foundation
- [ ] FastAPI app skeleton with WebSocket support
- [ ] Tauri shell pointing to FastAPI dev server
- [ ] SQLite database setup with SQLModel
- [ ] Workspace selection and initialization
- [ ] Basic React UI layout (sidebar, main panel, bottom panel)

### Phase 2: File Watching & Events
- [ ] watchfiles integration for folder monitoring
- [ ] Event bus (asyncio Queue + broadcast)
- [ ] Event persistence to SQLite
- [ ] Event Queue UI component with real-time updates
- [ ] WebSocket streaming of events to frontend

### Phase 3: Cards & Triggers
- [ ] Card schema and CRUD API
- [ ] Trigger matching (event → cards)
- [ ] Card list and detail UI
- [ ] Manual trigger ("Run Now" button)

### Phase 4: PydanticAI Agent
- [ ] PydanticAI agent setup with AI Gateway
- [ ] Chat interface UI
- [ ] Card creation from natural language
- [ ] Python code generation
- [ ] Interaction primitives (confirmation, choice, etc.)

### Phase 5: Execution Engine
- [ ] Sandbox executor (venv creation, isolated execution)
- [ ] Temporal integration (embedded server)
- [ ] CardExecutionWorkflow implementation
- [ ] Execution history and logging
- [ ] Retry logic

### Phase 6: MCP Integration
- [ ] MCP client manager
- [ ] MCP server configuration UI
- [ ] Agent with MCP tools
- [ ] Cards that query external data

### Phase 7: Polish
- [ ] Error handling and user-friendly messages
- [ ] Onboarding flow (first workspace setup)
- [ ] System tray integration
- [ ] Keyboard shortcuts
- [ ] Dark mode

---

## Dependencies

Managed via UV. Initialize with `uv init` and add dependencies with `uv add`.

```toml
# pyproject.toml
[project]
name = "leaf"
version = "0.1.0"
description = "Local Event-Driven Automation Framework"
requires-python = ">=3.11"
dependencies = [
    # Web framework
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "websockets>=14.0",

    # AI
    "pydantic-ai>=0.0.30",

    # Database
    "sqlmodel>=0.0.22",
    "aiosqlite>=0.20.0",

    # File watching
    "watchfiles>=1.0.0",

    # Workflow engine
    "temporalio>=1.7.0",

    # Utilities
    "python-slugify>=8.0.0",
    "python-dotenv>=1.0.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.8.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

---

## Environment Variables

```bash
# Required
PYDANTIC_AI_GATEWAY_API_KEY=your-api-key

# Optional
LEAF_PORT=8000
LEAF_LOG_LEVEL=info
LEAF_MODEL=gateway/google:gemini-2.5-flash
```

---

## Security Considerations

### Sandboxed Execution

1. **Isolated environments**: Each card's program runs in its own UV-managed environment
2. **Working directory**: Programs can only write to workspace
3. **Timeout**: All executions have configurable timeouts
4. **No shell expansion**: Commands run via `uv run` without shell=True
5. **Dependency isolation**: UV lockfiles ensure reproducible, isolated dependencies per card

### Code Generation Safety

1. **Review before creation**: Users see generated code before confirming
2. **Dependency allowlist**: Option to restrict pip packages
3. **Audit log**: All executions recorded with full stdout/stderr

### MCP Security

1. **User-configured servers**: Only servers explicitly added by user
2. **Per-server permissions**: Cards specify which MCP servers they can use
3. **Credential isolation**: API keys stored in system keychain (future)

---

## Open Questions

1. **Code editing**: Should users be able to edit generated code directly in the UI?
2. **Card versioning**: Track changes to cards/programs over time?
3. **Card sharing**: Export/import cards as JSON bundles?
4. **Multi-workspace**: Support multiple workspaces in one app instance?
5. **Remote Temporal**: Option to connect to external Temporal cluster?

---

## Getting Started

### Prerequisites

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Temporal CLI
brew install temporal

# Install Node.js (for frontend)
brew install node
```

### Development Setup

```bash
# Clone the repository
git clone https://github.com/yourorg/leaf.git
cd leaf

# Install Python dependencies with UV
uv sync

# Install frontend dependencies
cd frontend && npm install && cd ..

# Start all services (in separate terminals)

# Terminal 1: Temporal dev server
temporal server start-dev

# Terminal 2: FastAPI backend
uv run uvicorn leaf.main:app --reload

# Terminal 3: Tauri dev mode
cd tauri && cargo tauri dev
```

### Quick Commands

```bash
# Add a new dependency
uv add <package>

# Add a dev dependency
uv add --group dev <package>

# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Run the app
uv run python -m leaf.main
```

### First Card End-to-End

Focus on getting a single Card working:

1. User describes automation in chat
2. Agent generates card + Python code
3. User confirms creation
4. File is added to watched folder
5. Card executes via `uv run main.py`
6. Event appears in queue with result
