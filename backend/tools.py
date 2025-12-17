"""
Function definitions for OpenAI Realtime Agent integration.

This module provides tool definitions that can be used by the OpenAI Realtime
Agent to interact with Claude Code and the local development environment.

Each function is decorated with @function_tool to make it compatible with
the OpenAI Realtime Agent's function calling system.
"""

import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

from agents import function_tool

from claude_code_manager import ClaudeCodeManager

logger = logging.getLogger(__name__)


# Global Claude Code manager instance
# This is shared across all function calls to maintain process state
_claude_manager: Optional[ClaudeCodeManager] = None


def _get_claude_manager() -> ClaudeCodeManager:
    """
    Get or create the global Claude Code manager instance.

    Returns:
        ClaudeCodeManager: The singleton manager instance.
    """
    global _claude_manager
    if _claude_manager is None:
        _claude_manager = ClaudeCodeManager()
    return _claude_manager


@function_tool
async def ask_claude_code(task: str) -> str:
    """
    Ask Claude Code to perform a coding task.

    This function spawns a Claude Code subprocess and executes the given task.
    It streams the output and returns the complete result when finished.

    Args:
        task: A natural language description of the coding task to perform.
              Examples:
              - "Add a login endpoint to my FastAPI server"
              - "Fix the bug in the authentication module"
              - "Refactor the user service to use dependency injection"

    Returns:
        str: The complete output from Claude Code, including any files modified,
             commands run, and summary of changes made.

    Example:
        ```python
        result = await ask_claude_code("Add type hints to all functions in utils.py")
        print(result)
        ```
    """
    logger.info(f"Claude Code task requested: {task}")

    try:
        manager = _get_claude_manager()
        output_lines = []

        async for line in manager.run_task(task):
            output_lines.append(line)
            # Optionally log progress
            logger.debug(f"Claude Code output: {line.strip()}")

        result = "".join(output_lines)
        logger.info("Claude Code task completed successfully")
        return result

    except Exception as e:
        error_msg = f"Error executing Claude Code task: {str(e)}"
        logger.error(error_msg)
        return error_msg


@function_tool
def read_file(path: str) -> str:
    """
    Read a file from the project.

    This function safely reads a file from the local filesystem and returns
    its contents as a string. It handles various error cases like missing
    files or permission issues.

    Args:
        path: Relative or absolute path to the file to read.
              If relative, it's resolved from the current working directory.

    Returns:
        str: The contents of the file, or an error message if the file
             cannot be read.

    Example:
        ```python
        content = read_file("src/main.py")
        print(content)
        ```
    """
    logger.info(f"Reading file: {path}")

    try:
        file_path = Path(path).resolve()

        # Security check: ensure the file exists and is a file
        if not file_path.exists():
            return f"Error: File not found: {path}"

        if not file_path.is_file():
            return f"Error: Path is not a file: {path}"

        # Read the file
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        logger.info(f"Successfully read file: {path} ({len(content)} characters)")
        return content

    except PermissionError:
        error_msg = f"Error: Permission denied reading file: {path}"
        logger.error(error_msg)
        return error_msg

    except Exception as e:
        error_msg = f"Error reading file {path}: {str(e)}"
        logger.error(error_msg)
        return error_msg


@function_tool
def run_command(command: str, cwd: Optional[str] = None) -> str:
    """
    Run a shell command in the project directory.

    This function executes a shell command and returns the output. It runs
    commands synchronously with a timeout to prevent hanging.

    Args:
        command: The shell command to execute.
                 Examples: "npm test", "git status", "python -m pytest"
        cwd: Optional working directory for the command. If not provided,
             uses the current working directory.

    Returns:
        str: The combined stdout and stderr output from the command,
             or an error message if execution failed.

    Example:
        ```python
        result = run_command("git status")
        print(result)
        ```

    Warning:
        This function executes arbitrary shell commands. Ensure that commands
        come from trusted sources to avoid security issues.
    """
    logger.info(f"Running command: {command}")

    try:
        # Resolve working directory
        working_dir = Path(cwd).resolve() if cwd else Path.cwd()

        if not working_dir.exists():
            return f"Error: Working directory does not exist: {cwd}"

        # Execute the command with timeout
        result = subprocess.run(
            command,
            shell=True,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=30,  # 30 second timeout
        )

        # Combine stdout and stderr
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\nstderr:\n{result.stderr}"

        # Add return code if non-zero
        if result.returncode != 0:
            output += f"\n\nCommand exited with code {result.returncode}"

        logger.info(f"Command completed with return code {result.returncode}")
        return output

    except subprocess.TimeoutExpired:
        error_msg = f"Error: Command timed out after 30 seconds: {command}"
        logger.error(error_msg)
        return error_msg

    except Exception as e:
        error_msg = f"Error running command '{command}': {str(e)}"
        logger.error(error_msg)
        return error_msg


@function_tool
def search_codebase(pattern: str, path: Optional[str] = None, file_pattern: Optional[str] = None) -> str:
    """
    Search for code patterns in the codebase.

    This function uses `grep` (or `ripgrep` if available) to search for patterns
    in the codebase. It returns matching lines with file names and line numbers.

    Args:
        pattern: The search pattern (supports regex).
                 Examples: "def.*login", "TODO:", "class.*Service"
        path: Optional directory to search in. Defaults to current directory.
        file_pattern: Optional glob pattern to filter files.
                     Examples: "*.py", "*.ts", "src/**/*.js"

    Returns:
        str: Search results showing matching lines with file names and line numbers,
             or an error message if the search failed.

    Example:
        ```python
        results = search_codebase("def login", path="src", file_pattern="*.py")
        print(results)
        ```
    """
    logger.info(f"Searching codebase for pattern: {pattern}")

    try:
        # Build the search command
        # Try to use ripgrep (rg) if available, fall back to grep
        search_dir = Path(path).resolve() if path else Path.cwd()

        if not search_dir.exists():
            return f"Error: Search directory does not exist: {path}"

        # Check if ripgrep is available
        try:
            subprocess.run(
                ["rg", "--version"],
                capture_output=True,
                check=True,
                timeout=1
            )
            use_rg = True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            use_rg = False

        # Build command
        if use_rg:
            cmd = ["rg", "--line-number", "--no-heading", "--color=never"]
            if file_pattern:
                cmd.extend(["--glob", file_pattern])
            cmd.extend([pattern, str(search_dir)])
        else:
            cmd = ["grep", "-r", "-n", "-I"]  # -I skips binary files
            if file_pattern:
                cmd.extend(["--include", file_pattern])
            cmd.extend([pattern, str(search_dir)])

        # Execute search
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Note: grep returns non-zero if no matches found, which is not an error
        if result.returncode == 0:
            matches = result.stdout
            match_count = len(matches.strip().split('\n')) if matches.strip() else 0
            logger.info(f"Found {match_count} matches for pattern: {pattern}")
            return matches if matches else "No matches found."
        elif result.returncode == 1:
            # No matches found (grep convention)
            logger.info(f"No matches found for pattern: {pattern}")
            return "No matches found."
        else:
            # Actual error
            error_msg = f"Search failed: {result.stderr}"
            logger.error(error_msg)
            return error_msg

    except subprocess.TimeoutExpired:
        error_msg = f"Error: Search timed out after 30 seconds"
        logger.error(error_msg)
        return error_msg

    except Exception as e:
        error_msg = f"Error searching codebase: {str(e)}"
        logger.error(error_msg)
        return error_msg


# List of all available tools for export
REALTIME_TOOLS = [
    ask_claude_code,
    read_file,
    run_command,
    search_codebase,
]
