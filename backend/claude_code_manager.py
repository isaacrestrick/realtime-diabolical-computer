"""
Claude Code Process Manager

Manages a subprocess running the Claude Code CLI (`claude` command) for
executing coding tasks. Provides streaming output and lifecycle management.
"""

import asyncio
import logging
import signal
from asyncio.subprocess import Process
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)


class ClaudeCodeError(Exception):
    """Base exception for Claude Code manager errors."""
    pass


class ProcessStartError(ClaudeCodeError):
    """Raised when the Claude Code process fails to start."""
    pass


class ProcessCommunicationError(ClaudeCodeError):
    """Raised when communication with the process fails."""
    pass


class ClaudeCodeManager:
    """
    Manages the lifecycle of a Claude Code CLI subprocess.

    This class handles:
    - Spawning the `claude` CLI process
    - Streaming output from the process
    - Graceful shutdown and cleanup
    - Error handling for process failures

    Example:
        ```python
        manager = ClaudeCodeManager()
        async for output in manager.run_task("Add a login endpoint to my FastAPI server"):
            print(output, end="", flush=True)
        await manager.stop()
        ```
    """

    def __init__(self, claude_binary: str = "claude"):
        """
        Initialize the Claude Code manager.

        Args:
            claude_binary: Path to the `claude` CLI binary. Defaults to "claude"
                          which assumes it's in the system PATH.
        """
        self.claude_binary = claude_binary
        self._process: Optional[Process] = None
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """Check if the Claude Code process is currently running."""
        return self._is_running and self._process is not None

    async def run_task(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Execute a coding task using Claude Code and stream the output.

        This method spawns a new `claude` CLI process with the given prompt,
        streams the output line by line, and properly cleans up when done.

        Args:
            prompt: The task description to send to Claude Code.

        Yields:
            str: Lines of output from the Claude Code process.

        Raises:
            ProcessStartError: If the process fails to start.
            ProcessCommunicationError: If communication with the process fails.

        Example:
            ```python
            manager = ClaudeCodeManager()
            async for line in manager.run_task("Fix the bug in auth.py"):
                print(line)
            ```
        """
        try:
            # Start the Claude Code process
            self._process = await asyncio.create_subprocess_exec(
                self.claude_binary,
                prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
            )
            self._is_running = True
            logger.info(f"Started Claude Code process (PID: {self._process.pid})")

            # Stream stdout
            if self._process.stdout:
                async for line in self._process.stdout:
                    decoded_line = line.decode('utf-8', errors='replace')
                    yield decoded_line

            # Wait for process to complete
            return_code = await self._process.wait()

            # Check for errors
            if return_code != 0:
                stderr_output = ""
                if self._process.stderr:
                    stderr_data = await self._process.stderr.read()
                    stderr_output = stderr_data.decode('utf-8', errors='replace')

                logger.error(
                    f"Claude Code process exited with code {return_code}. "
                    f"stderr: {stderr_output}"
                )
                raise ProcessCommunicationError(
                    f"Process exited with code {return_code}: {stderr_output}"
                )

            logger.info(f"Claude Code process completed successfully")

        except FileNotFoundError:
            error_msg = (
                f"Claude CLI binary '{self.claude_binary}' not found. "
                "Please ensure Claude Code is installed and in your PATH."
            )
            logger.error(error_msg)
            raise ProcessStartError(error_msg)

        except Exception as e:
            logger.error(f"Error running Claude Code task: {e}")
            raise ProcessCommunicationError(f"Failed to run task: {e}")

        finally:
            self._is_running = False
            self._process = None

    async def stop(self, timeout: float = 5.0) -> None:
        """
        Gracefully stop the Claude Code process.

        Sends SIGTERM to the process and waits for it to exit. If it doesn't
        exit within the timeout, sends SIGKILL to force termination.

        Args:
            timeout: Maximum time in seconds to wait for graceful shutdown.
                    Defaults to 5.0 seconds.
        """
        if not self._process:
            logger.debug("No process to stop")
            return

        if self._process.returncode is not None:
            logger.debug("Process already terminated")
            self._is_running = False
            self._process = None
            return

        try:
            logger.info(f"Stopping Claude Code process (PID: {self._process.pid})")

            # Send SIGTERM for graceful shutdown
            self._process.send_signal(signal.SIGTERM)

            try:
                # Wait for process to exit
                await asyncio.wait_for(self._process.wait(), timeout=timeout)
                logger.info("Process stopped gracefully")
            except asyncio.TimeoutError:
                # Force kill if timeout exceeded
                logger.warning(
                    f"Process did not stop within {timeout}s, sending SIGKILL"
                )
                self._process.kill()
                await self._process.wait()
                logger.info("Process forcefully terminated")

        except ProcessLookupError:
            logger.debug("Process already terminated")

        except Exception as e:
            logger.error(f"Error stopping process: {e}")

        finally:
            self._is_running = False
            self._process = None

    async def kill(self) -> None:
        """
        Forcefully terminate the Claude Code process.

        Sends SIGKILL to immediately terminate the process without cleanup.
        Use stop() for graceful shutdown when possible.
        """
        if not self._process:
            logger.debug("No process to kill")
            return

        if self._process.returncode is not None:
            logger.debug("Process already terminated")
            self._is_running = False
            self._process = None
            return

        try:
            logger.warning(f"Killing Claude Code process (PID: {self._process.pid})")
            self._process.kill()
            await self._process.wait()
            logger.info("Process killed")

        except ProcessLookupError:
            logger.debug("Process already terminated")

        except Exception as e:
            logger.error(f"Error killing process: {e}")

        finally:
            self._is_running = False
            self._process = None

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures process cleanup."""
        await self.stop()
