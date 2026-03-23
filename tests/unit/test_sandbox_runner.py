"""Tests for SandboxRunner: Phase 4 Docker-based sandboxed execution."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.models.common import EvalScenario
from loom.models.eval import CodeBlock, SandboxResult
from loom.services.sandbox_runner import SandboxRunner


def _make_scenario(**overrides: object) -> EvalScenario:
    defaults = {
        "description": "test scenario",
        "input_context": "test context",
        "success_criteria": "should pass",
    }
    defaults.update(overrides)
    return EvalScenario(**defaults)


def _make_code_block(**overrides: object) -> CodeBlock:
    defaults = {
        "language": "python",
        "code": "print('hello')",
        "line_start": 1,
    }
    defaults.update(overrides)
    return CodeBlock(**defaults)


class _AsyncIterator:
    """Async iterator that yields pre-configured chunks."""

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks
        self._index = 0

    def __aiter__(self):  # noqa: ANN204
        return self

    async def __anext__(self) -> bytes:
        if self._index >= len(self._chunks):
            raise StopAsyncIteration
        chunk = self._chunks[self._index]
        self._index += 1
        return chunk


class _HangingAsyncIterator:
    """Async iterator that blocks indefinitely (for timeout tests)."""

    def __aiter__(self):  # noqa: ANN204
        return self

    async def __anext__(self) -> bytes:
        await asyncio.sleep(999)
        raise StopAsyncIteration  # pragma: no cover


def _make_stream(chunks: list[bytes]) -> MagicMock:
    """Build a mock stream with async iteration support."""
    iterator = _AsyncIterator(chunks)
    stream = MagicMock()
    stream.write_in = AsyncMock()
    stream.feed_eof = MagicMock()
    stream.__aiter__ = lambda _self: iterator.__aiter__()
    stream.__anext__ = lambda _self: iterator.__anext__()
    return stream


def _make_docker_mock(
    stdout_data: dict | None = None,
    exit_code: int = 0,
    hanging: bool = False,
) -> AsyncMock:
    """Build a mock aiodocker.Docker client with container lifecycle."""
    if stdout_data is None:
        stdout_data = {
            "passed": True,
            "scenarios_run": 1,
            "scenarios_passed": 1,
            "errors": [],
            "lint_warnings": [],
        }

    stdout_bytes = json.dumps(stdout_data).encode()

    if hanging:
        stream = MagicMock()
        stream.write_in = AsyncMock()
        stream.feed_eof = MagicMock()
        hanging_iter = _HangingAsyncIterator()
        stream.__aiter__ = lambda _self: hanging_iter.__aiter__()
        stream.__anext__ = lambda _self: hanging_iter.__anext__()
    else:
        stream = _make_stream([stdout_bytes])

    # Mock container
    container = AsyncMock()
    container.start = AsyncMock()
    container.wait = AsyncMock(return_value={"StatusCode": exit_code})
    container.delete = AsyncMock()
    container.attach = MagicMock(return_value=stream)

    # Mock docker client
    docker = AsyncMock()
    docker.containers = AsyncMock()
    docker.containers.create_or_replace = AsyncMock(return_value=container)

    return docker


class TestSandboxRunner:
    @pytest.mark.asyncio
    async def test_successful_execution(self) -> None:
        expected = {
            "passed": True,
            "scenarios_run": 1,
            "scenarios_passed": 1,
            "errors": [],
            "lint_warnings": [],
        }
        docker = _make_docker_mock(stdout_data=expected)
        runner = SandboxRunner(docker, timeout_seconds=10)

        result = await runner.execute(
            eval_scenarios=[_make_scenario()],
            code_blocks=[_make_code_block()],
        )

        assert isinstance(result, SandboxResult)
        assert result.passed is True
        assert result.scenarios_run == 1
        assert result.scenarios_passed == 1
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_container_security_config(self) -> None:
        docker = _make_docker_mock()
        runner = SandboxRunner(docker, memory_mb=512)

        await runner.execute(
            eval_scenarios=[_make_scenario()],
            code_blocks=[],
        )

        create_call = docker.containers.create_or_replace
        assert create_call.called
        config = create_call.call_args.kwargs["config"]

        assert config["NetworkDisabled"] is True
        host = config["HostConfig"]
        assert host["ReadonlyRootfs"] is True
        assert host["CapDrop"] == ["ALL"]
        assert host["Memory"] == 512 * 1024 * 1024
        assert host["PidsLimit"] == 64
        assert host["SecurityOpt"] == ["no-new-privileges"]

    @pytest.mark.asyncio
    async def test_container_deleted_after_execution(self) -> None:
        docker = _make_docker_mock()
        runner = SandboxRunner(docker, timeout_seconds=10)

        await runner.execute(
            eval_scenarios=[_make_scenario()],
            code_blocks=[],
        )

        container = docker.containers.create_or_replace.return_value
        container.delete.assert_called_once_with(force=True)

    @pytest.mark.asyncio
    async def test_timeout_produces_failure(self) -> None:
        docker = _make_docker_mock(hanging=True)

        runner = SandboxRunner(docker, timeout_seconds=0.1)

        result = await runner.execute(
            eval_scenarios=[_make_scenario()],
            code_blocks=[],
        )

        assert result.passed is False
        assert any("timed out" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_container_deleted_on_timeout(self) -> None:
        docker = _make_docker_mock(hanging=True)

        runner = SandboxRunner(docker, timeout_seconds=0.1)

        await runner.execute(
            eval_scenarios=[_make_scenario()],
            code_blocks=[],
        )

        container = docker.containers.create_or_replace.return_value
        container.delete.assert_called_once_with(force=True)

    @pytest.mark.asyncio
    async def test_nonzero_exit_code_handled(self) -> None:
        error_output = {
            "passed": False,
            "scenarios_run": 0,
            "scenarios_passed": 0,
            "errors": ["Runner error: something broke"],
            "lint_warnings": [],
        }
        docker = _make_docker_mock(stdout_data=error_output, exit_code=1)
        runner = SandboxRunner(docker, timeout_seconds=10)

        result = await runner.execute(
            eval_scenarios=[_make_scenario()],
            code_blocks=[],
        )

        assert result.passed is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_empty_stdout_handled(self) -> None:
        docker = _make_docker_mock()
        container = docker.containers.create_or_replace.return_value

        stream = _make_stream([b""])
        container.attach = MagicMock(return_value=stream)

        runner = SandboxRunner(docker, timeout_seconds=10)

        result = await runner.execute(
            eval_scenarios=[_make_scenario()],
            code_blocks=[],
        )

        assert result.passed is False
        assert any("no output" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_malformed_json_handled(self) -> None:
        docker = _make_docker_mock()
        container = docker.containers.create_or_replace.return_value

        stream = _make_stream([b"not valid json {"])
        container.attach = MagicMock(return_value=stream)

        runner = SandboxRunner(docker, timeout_seconds=10)

        result = await runner.execute(
            eval_scenarios=[_make_scenario()],
            code_blocks=[],
        )

        assert result.passed is False
        assert any("parse" in e.lower() for e in result.errors)
