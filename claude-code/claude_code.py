"""Claude Code CLI as an Agentix namespace.

Usage:

    from agentix import RuntimeClient
    import claude_code

    async with RuntimeClient(sandbox.runtime_url) as c:
        r = await c.remote(
            claude_code.run,
            instruction="Fix the failing test in tests/test_foo.py",
            workdir="/testbed",
            env={"ANTHROPIC_API_KEY": api_key},
        )
        print(r.exit_code, r.patch)

Top-level module — no `src/agentix/` layer. The `agentix.namespace`
entry point in `pyproject.toml` points at this module by import name,
which is all the framework needs.
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

    `patch` is the unified diff of all changes the agent made to
    `workdir`, captured via `git add -A && git diff --cached` after
    claude exits — works whether the agent committed, staged, or just
    modified files in place.
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
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        proc.kill()
        await proc.communicate()
        return RunResult(exit_code=-1, stdout="", stderr=f"claude timed out after {timeout}s", patch="")

    return RunResult(
        exit_code=proc.returncode or 0,
        stdout=stdout.decode(errors="replace"),
        stderr=stderr.decode(errors="replace"),
        patch=await _diff(workdir),
    )


async def _diff(workdir: str) -> str:
    """All agent changes as a unified diff, including untracked files."""
    add = await asyncio.create_subprocess_exec(
        "git", "add", "-A", cwd=workdir,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
    )
    await add.wait()
    diff = await asyncio.create_subprocess_exec(
        "git", "diff", "--cached", "--no-color", cwd=workdir,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    out, _ = await diff.communicate()
    return out.decode(errors="replace")
