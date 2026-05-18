"""Host-side orchestrator: evaluate Claude Code on SWE-bench Verified.

Per instance:
  1. clone the repo at `base_commit` via `bash.run`
  2. `cc.run(...)` against the testbed
  3. `bash.run(...)` to extract the patch (`git add -A && git diff --cached`)
  4. `swe.score(...)` to apply the patch + run the harness

Run as `python -m runner --limit N` (see `__main__.py`).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from agentix import RuntimeClient, bash
from agentix.deployment.base import SandboxConfig, session
from agentix.deployment.docker import DockerDeployment
from datasets import load_dataset

import cc
import swe

WORKDIR = "/testbed"


async def solve_one(c: RuntimeClient, inst: dict, api_key: str) -> None:
    iid = inst["instance_id"]
    print(f"[{iid}] cloning {inst['repo']}@{inst['base_commit'][:12]}")
    await c.remote(
        bash.run,
        command=(
            f"rm -rf {WORKDIR} && "
            f"git clone --quiet https://github.com/{inst['repo']}.git {WORKDIR} && "
            f"cd {WORKDIR} && git checkout --quiet {inst['base_commit']}"
        ),
        timeout=600,
    )

    print(f"[{iid}] running claude")
    out = await c.remote(
        cc.run,
        instruction=inst["problem_statement"],
        workdir=WORKDIR,
        timeout=900,
        env={"ANTHROPIC_API_KEY": api_key},
    )

    patch = await _extract_patch(c, WORKDIR)
    print(f"[{iid}] claude exit={out.exit_code} patch_bytes={len(patch)}")
    if not patch:
        print(f"[{iid}] no patch produced — skipping score")
        return

    s = await c.remote(swe.score, instance=inst, patch=patch)
    verdict = "PASS" if s.resolved else "FAIL"
    ftp_total = len(s.fail_to_pass_resolved) + len(s.fail_to_pass_missing)
    print(
        f"[{iid}] {verdict}  patch_applied={s.patch_applied}  "
        f"resolved={len(s.fail_to_pass_resolved)}/{ftp_total}  "
        f"regressions={len(s.pass_to_pass_broken)}"
    )


async def _extract_patch(c: RuntimeClient, workdir: str) -> str:
    """All changes in `workdir` as a unified diff, including untracked files."""
    r = await c.remote(
        bash.run,
        command=f"cd {workdir} && git add -A && git diff --cached --no-color",
        timeout=60,
    )
    return r.stdout if r.exit_code == 0 else ""


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="runner", description=__doc__.splitlines()[0])
    parser.add_argument(
        "--image", default="eval-cc-swe:0.1.0",
        help="Bundle image produced by `agentix build .`.",
    )
    parser.add_argument(
        "--limit", type=int, default=1,
        help="Number of SWE-bench instances to run.",
    )
    args = parser.parse_args(argv)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("error: ANTHROPIC_API_KEY is not set", file=sys.stderr)
        return 2

    ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
    instances = [dict(ds[i]) for i in range(args.limit)]

    cfg = SandboxConfig(image=args.image)
    async with session(DockerDeployment(), cfg) as sandbox:
        print(f"sandbox up: {sandbox.runtime_url}")
        async with RuntimeClient(sandbox.runtime_url) as c:
            for inst in instances:
                await solve_one(c, inst, api_key)
    return 0


__all__ = ["main", "solve_one"]
