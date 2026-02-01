"""Sandbox executor for running card programs.

Runs Python programs in isolated UV-managed environments.
"""

import asyncio
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class ExecutionResult:
    """Result of a sandbox execution."""

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    error: str | None = None


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""

    card_id: str
    program_path: Path  # Absolute path to program directory
    working_dir: Path  # Project root (where program can write)
    timeout_seconds: int = 300
    dependencies: list[str] = field(default_factory=list)


class Sandbox:
    """Isolated execution environment for card programs.

    Uses UV to create and manage isolated Python environments.
    """

    def __init__(self, config: SandboxConfig) -> None:
        """Initialize the sandbox.

        Args:
            config: Sandbox configuration
        """
        self.config = config
        self._venv_path: Path | None = None

    @property
    def venv_path(self) -> Path:
        """Get the virtual environment path for this card."""
        return self.config.program_path / ".venv"

    async def setup(self) -> None:
        """Set up the isolated environment.

        Creates a UV virtual environment and installs dependencies.
        """
        program_path = self.config.program_path

        # Ensure program directory exists
        if not program_path.exists():
            raise FileNotFoundError(f"Program directory not found: {program_path}")

        # Check if main.py exists
        main_file = program_path / "main.py"
        if not main_file.exists():
            raise FileNotFoundError(f"main.py not found in {program_path}")

        # Create pyproject.toml if it doesn't exist
        pyproject = program_path / "pyproject.toml"
        if not pyproject.exists():
            await self._create_pyproject()

        # Create/sync the virtual environment
        await self._sync_environment()

    async def _create_pyproject(self) -> None:
        """Create a pyproject.toml for the program."""
        deps = self.config.dependencies or []
        deps_str = ", ".join(f'"{dep}"' for dep in deps)

        content = f'''[project]
name = "card-{self.config.card_id}"
version = "0.1.0"
description = "Generated card program"
requires-python = ">=3.11"
dependencies = [{deps_str}]
'''
        pyproject = self.config.program_path / "pyproject.toml"
        pyproject.write_text(content)

    async def _sync_environment(self) -> None:
        """Create and sync the UV environment."""
        program_path = self.config.program_path

        # Run uv sync to create venv and install dependencies
        process = await asyncio.create_subprocess_exec(
            "uv",
            "sync",
            "--quiet",
            cwd=str(program_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"Failed to sync environment: {error_msg}")

    async def run(
        self,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """Run the program in the sandbox.

        Args:
            args: Command-line arguments to pass to main.py
            env: Additional environment variables

        Returns:
            ExecutionResult with stdout, stderr, and status
        """
        started_at = datetime.now()
        program_path = self.config.program_path
        working_dir = self.config.working_dir

        # Build the command: uv run main.py [args...]
        cmd = ["uv", "run", "python", "main.py"]
        if args:
            cmd.extend(args)

        # Set up environment
        run_env = os.environ.copy()
        run_env["LEAF_PROJECT_ROOT"] = str(working_dir)
        run_env["LEAF_CARD_ID"] = self.config.card_id
        if env:
            run_env.update(env)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(program_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=run_env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.timeout_seconds,
                )
                exit_code = process.returncode or 0
                error = None

            except asyncio.TimeoutError:
                # Kill the process on timeout
                process.kill()
                await process.wait()
                stdout = b""
                stderr = b"Execution timed out"
                exit_code = -1
                error = f"Timeout after {self.config.timeout_seconds} seconds"

        except Exception as e:
            stdout = b""
            stderr = str(e).encode()
            exit_code = -1
            error = str(e)

        completed_at = datetime.now()
        duration = (completed_at - started_at).total_seconds()

        return ExecutionResult(
            success=exit_code == 0,
            exit_code=exit_code,
            stdout=stdout.decode() if isinstance(stdout, bytes) else stdout,
            stderr=stderr.decode() if isinstance(stderr, bytes) else stderr,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            error=error,
        )

    async def teardown(self) -> None:
        """Clean up the sandbox environment.

        Note: We don't delete the venv by default to speed up subsequent runs.
        """
        pass

    async def cleanup_venv(self) -> None:
        """Remove the virtual environment completely.

        Call this when deleting a card to free disk space.
        """
        if self.venv_path.exists():
            shutil.rmtree(self.venv_path)


async def run_card_program(
    program_path: Path,
    working_dir: Path,
    card_id: str,
    trigger_file: Path | None = None,
    timeout_seconds: int = 300,
    dependencies: list[str] | None = None,
) -> ExecutionResult:
    """Convenience function to run a card's program.

    Args:
        program_path: Path to the program directory
        working_dir: Project root directory
        card_id: The card ID
        trigger_file: Path to the file that triggered the execution
        timeout_seconds: Maximum execution time
        dependencies: Python packages to install

    Returns:
        ExecutionResult with execution details
    """
    config = SandboxConfig(
        card_id=card_id,
        program_path=program_path,
        working_dir=working_dir,
        timeout_seconds=timeout_seconds,
        dependencies=dependencies or [],
    )

    sandbox = Sandbox(config)

    try:
        await sandbox.setup()

        # Build args - pass trigger file path if provided
        args = []
        if trigger_file:
            args.append(str(trigger_file))

        return await sandbox.run(args=args)

    finally:
        await sandbox.teardown()
