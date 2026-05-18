"""Sandbox-side: invoke the `claude` CLI against a workdir.

Host orchestrator calls `c.remote(cc.run, instruction=..., workdir=...)`.
Routes by `cc.run.__module__` (= `cc`); the multiplexer auto-registers
the module on first dispatch.

Requires `claude` and `git` on PATH inside the sandbox — provided by
`default.nix` at the project root.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass


@dataclass
class Result:
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
) -> Result:
    """Run Claude Code against `workdir` with `instruction`.

    The caller is responsible for staging the repo at `workdir` (via
    `c.remote(bash.run, command="git clone …")` host-side) and for
    extracting the resulting patch afterwards.
    """
    cmd = ["claude", "-p", instruction, "--print",
           "--permission-mode", "bypassPermissions"]
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
        return Result(exit_code=-1, stdout="", stderr=f"claude timed out after {timeout}s")

    return Result(
        exit_code=proc.returncode or 0,
        stdout=stdout.decode(errors="replace"),
        stderr=stderr.decode(errors="replace"),
    )
