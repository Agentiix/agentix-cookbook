"""End-to-end: SWE-bench Verified × Claude Code, all on Agentix.

Prereqs:
    pip install -e ./claude-code -e ./swebench   # so the namespaces are
                                                  # importable on the caller
    agentix build bash files claude-code swebench -o cookbook:0.1.0
    export ANTHROPIC_API_KEY=sk-...

Run:
    python examples/swebench_with_claude_code.py            # one instance
    python examples/swebench_with_claude_code.py --limit 5  # five
    python examples/swebench_with_claude_code.py --image my-cookbook:0.2.0

The script deploys a local sandbox from the bundle image, fetches one
SWE-bench instance, hands the problem to Claude Code, scores the
resulting patch with SWE-bench's held-out tests, and tears the
sandbox down on exit.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from agentix import RuntimeClient, SandboxConfig, claude_code, swebench
from agentix.deployment.base import session
from agentix.deployment.docker import DockerDeployment


async def solve_one(c: RuntimeClient, instance_id: str, api_key: str) -> None:
    print(f"[{instance_id}] fetching task …")
    task = await c.remote(swebench.get_task, instance_id=instance_id)
    print(f"[{instance_id}] workdir={task.workdir} problem={task.problem[:120]!r}")

    print(f"[{instance_id}] running claude_code …")
    cc = await c.remote(
        claude_code.run,
        instruction=task.problem,
        workdir=task.workdir,
        timeout=900,
        env={"ANTHROPIC_API_KEY": api_key},
    )
    print(f"[{instance_id}] claude exit={cc.exit_code} patch_bytes={len(cc.patch)}")

    if not cc.patch:
        print(f"[{instance_id}] no patch produced — skipping score")
        return

    print(f"[{instance_id}] scoring …")
    s = await c.remote(swebench.score, instance_id=instance_id, patch=cc.patch)
    verdict = "PASS" if s.passed else "FAIL"
    print(f"[{instance_id}] {verdict}  "
          f"resolved={len(s.fail_to_pass_resolved)}/{len(s.fail_to_pass_resolved) + len(s.fail_to_pass_missing)}  "
          f"regressions={len(s.pass_to_pass_broken)}")


async def main(args: argparse.Namespace) -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("error: ANTHROPIC_API_KEY is not set", file=sys.stderr)
        return 2

    cfg = SandboxConfig(image=args.image)
    deployment = DockerDeployment()

    async with session(deployment, cfg) as sandbox:
        print(f"sandbox up: {sandbox.runtime_url}")
        async with RuntimeClient(sandbox.runtime_url) as c:
            ids = await c.remote(swebench.list_ids, limit=args.limit)
            for instance_id in ids:
                await solve_one(c, instance_id, api_key)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--image", default="cookbook:0.1.0",
                        help="Bundle image produced by `agentix build`.")
    parser.add_argument("--limit", type=int, default=1,
                        help="Number of SWE-bench instances to run.")
    raise SystemExit(asyncio.run(main(parser.parse_args())))
