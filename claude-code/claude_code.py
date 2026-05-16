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
        print(r.exit_code, r.stdout)

The namespace owns one thing: invoking the `claude` CLI and reporting
what it printed. Turning the agent's workspace changes into a patch
(or anything else downstream) is the caller's concern — typically a
`bash.run("git add -A && git diff --cached")` on the host side.
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


async def run(
    instruction: str,
    *,
    workdir: str = "/testbed",
    timeout: float = 600,
    model: str | None = None,
    max_turns: int | None = None,
    env: dict[str, str] | None = None,
) -> RunResult:
    """Run Claude Code against `workdir` with `instruction` and return its captured output."""
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
        return RunResult(exit_code=-1, stdout="", stderr=f"claude timed out after {timeout}s")

    return RunResult(
        exit_code=proc.returncode or 0,
        stdout=stdout.decode(errors="replace"),
        stderr=stderr.decode(errors="replace"),
    )
