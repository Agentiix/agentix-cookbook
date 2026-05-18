"""Host-side runner for the hello-agentix example.

Run this AFTER:

    1. uv sync (installs deps incl. agentixx, agentix-runtime-basic,
       agentix-deployment-docker into the example's venv)
    2. uv run agentix build . --name hello-agentix
       (produces the runtime image `hello-agentix:0.1.0` locally)

Then `uv run python run.py` and you should see something like:

    sandbox up at http://localhost:<port>
    exit=0 stdout='hello from Linux <kernel> ...'
"""

import asyncio

from agentix import RuntimeClient, SandboxConfig, session
from agentix.bash import run
from agentix.deployment.docker import DockerDeployment


async def main() -> None:
    deployment = DockerDeployment()
    config = SandboxConfig(
        # Task base image — the environment the workload runs in. Swap
        # this for any Linux image (Alpine, Ubuntu, a SWE-bench task
        # image); the runtime overlay is libc-independent because all
        # /nix/store binaries vendor their own closure.
        image="python:3.13-slim",
        # Bundle produced by `agentix build .` in this directory.
        runtime_image="hello-agentix:0.1.0",
    )
    async with session(deployment, config) as sandbox:
        print(f"sandbox up at {sandbox.runtime_url}")
        async with RuntimeClient(sandbox.runtime_url) as client:
            result = await client.remote(run, command="echo hello from $(uname -a)")
            print(f"exit={result.exit_code} stdout={result.stdout!r}")


if __name__ == "__main__":
    asyncio.run(main())
