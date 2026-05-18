"""Smallest Agentix sandbox-side module.

Nothing to declare — `agentix-runtime-basic` already exposes `bash.run`
and `files.upload/download` for the typical "run a command in a sandbox"
case. The host orchestrator in `run.py` calls `agentix.bash.run`
directly; this package is here only so the example's pyproject has
something to install.

If you want a custom function callable from the host, add it here:

    async def greet(name: str) -> str:
        return f"hello {name} from inside the sandbox"

Then on the host:

    from hello_agentix import greet
    await client.remote(greet, name="world")
"""
