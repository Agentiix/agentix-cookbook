"""Claude Code CLI as an Agentix namespace.

Usage:

    from agentix import RuntimeClient, claude_code

    async with RuntimeClient(sandbox.runtime_url) as c:
        result = await c.remote(
            claude_code.run,
            instruction="Fix the failing test in test_foo.py",
            workdir="/testbed",
        )
        print(result.exit_code, result.patch)

The namespace is module-shaped: `run` is the remote-callable surface,
`RunResult` is a regular type the caller imports for annotations.
Method bodies execute inside the sandbox; this module shells out to the
`claude` binary that the namespace's `default.nix` ships on PATH.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass


@dataclass
class RunResult:
    exit_code: int
    stdout: str
    stderr: str
    patch: str


async def run(
    instruction: str,
    *,
    workdir: str = "/testbed",
    timeout: float = 600,
    model: str | None = None,
    max_turns: int | None = None,
    env: dict[str, str] | None = None,
) -> RunResult:
    """Run Claude Code against `workdir` with `instruction` and return its output.

    `patch` is the unified diff of changes the agent made to `workdir`,
    computed by `git diff` after the agent exits — works whether the
    agent committed, staged, or just modified files in place.
    """
    cmd = ["claude", "-p", instruction, "--print", "--permission-mode", "bypassPermissions"]
    if model:
        cmd += ["--model", model]
    if max_turns is not None:
        cmd += ["--max-turns", str(max_turns)]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=workdir,
        env={**os.environ, **(env or {})},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout,
        )
    except TimeoutError:
        proc.kill()
        await proc.communicate()
        return RunResult(
            exit_code=-1,
            stdout="",
            stderr=f"claude timed out after {timeout}s",
            patch="",
        )

    return RunResult(
        exit_code=proc.returncode or 0,
        stdout=stdout_bytes.decode(errors="replace"),
        stderr=stderr_bytes.decode(errors="replace"),
        patch=await _extract_patch(workdir),
    )


async def _extract_patch(workdir: str) -> str:
    """Diff against HEAD, including untracked files, to capture all agent changes."""
    add_proc = await asyncio.create_subprocess_exec(
        "git", "add", "-A",
        cwd=workdir,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await add_proc.wait()

    diff_proc = await asyncio.create_subprocess_exec(
        "git", "diff", "--cached", "--no-color",
        cwd=workdir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await diff_proc.communicate()
    return stdout.decode(errors="replace")
