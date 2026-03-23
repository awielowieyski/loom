"""SandboxRunner: Phase 4 Docker-based sandboxed scenario execution.

Manages ephemeral Docker containers for isolated evaluation of code blocks
and scenarios using aiodocker.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

from loom.models.eval import SandboxResult

if TYPE_CHECKING:
    from loom.models.common import EvalScenario
    from loom.models.eval import CodeBlock

logger = logging.getLogger(__name__)

_DEFAULT_IMAGE = "loom-eval-sandbox:latest"
_DEFAULT_TIMEOUT = 30
_DEFAULT_MEMORY_MB = 256


class SandboxRunner:
    """Run evaluation scenarios inside ephemeral Docker containers."""

    def __init__(
        self,
        docker: Any,
        *,
        image: str = _DEFAULT_IMAGE,
        timeout_seconds: float = _DEFAULT_TIMEOUT,
        memory_mb: int = _DEFAULT_MEMORY_MB,
    ) -> None:
        self._docker = docker
        self._image = image
        self._timeout = timeout_seconds
        self._memory = memory_mb

    async def execute(
        self,
        eval_scenarios: list[EvalScenario],
        code_blocks: list[CodeBlock],
    ) -> SandboxResult:
        """Run scenarios and code blocks in a sandboxed container.

        Creates an ephemeral container with strict security constraints,
        sends input via stdin, and parses the JSON result from stdout.
        The container is always deleted in the finally block.
        """
        task_input = json.dumps(
            {
                "code_blocks": [cb.model_dump() for cb in code_blocks],
                "eval_scenarios": [es.model_dump() for es in eval_scenarios],
            }
        )

        container = None
        try:
            container = await self._docker.containers.create_or_replace(
                name=None,
                config=self._build_config(task_input),
            )
            result = await asyncio.wait_for(
                self._run_container(container, task_input),
                timeout=self._timeout,
            )
            return result

        except TimeoutError:
            logger.warning("Sandbox execution timed out after %ds", self._timeout)
            return SandboxResult(
                passed=False,
                errors=[f"Sandbox execution timed out after {self._timeout}s"],
            )
        except Exception as exc:
            logger.exception("Sandbox execution failed")
            return SandboxResult(
                passed=False,
                errors=[f"Sandbox execution error: {type(exc).__name__}: {exc}"],
            )
        finally:
            if container is not None:
                try:
                    await container.delete(force=True)
                except Exception:
                    logger.warning("Failed to delete sandbox container", exc_info=True)

    def _build_config(self, stdin_data: str) -> dict[str, Any]:
        """Build the Docker container configuration with security constraints."""
        return {
            "Image": self._image,
            "OpenStdin": True,
            "StdinOnce": True,
            "AttachStdin": True,
            "AttachStdout": True,
            "AttachStderr": True,
            "NetworkDisabled": True,
            "HostConfig": {
                "Memory": self._memory * 1024 * 1024,
                "NanoCpus": 500_000_000,
                "ReadonlyRootfs": True,
                "Tmpfs": {"/tmp": "rw,noexec,size=64m"},
                "CapDrop": ["ALL"],
                "PidsLimit": 64,
                "SecurityOpt": ["no-new-privileges"],
            },
        }

    async def _run_container(
        self,
        container: Any,
        task_input: str,
    ) -> SandboxResult:
        """Start container, send stdin, read stdout, parse result."""
        # Attach to container to get stdin/stdout streams
        stream = container.attach(stdin=True, stdout=True, stderr=True)

        await container.start()

        # Write task input to stdin
        await stream.write_in(task_input.encode())
        stream.feed_eof()

        # Read stdout
        output_parts: list[bytes] = []
        async for chunk in stream:
            output_parts.append(chunk)

        # Wait for container to finish
        await container.wait()

        stdout = b"".join(output_parts).decode().strip()

        if not stdout:
            return SandboxResult(
                passed=False,
                errors=["Sandbox produced no output"],
            )

        try:
            data = json.loads(stdout)
            return SandboxResult(**data)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            return SandboxResult(
                passed=False,
                errors=[f"Failed to parse sandbox output: {exc}"],
            )
