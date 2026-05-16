# `claude_code` — Claude Code as an Agentix namespace

A worked example of wrapping an agent CLI binary. The pattern
generalises to any single-binary agent (Aider, Codex, …) — copy
this directory, swap the Nix derivation's `src`, adjust the argv.

## Layout

```
claude-code/
├── pyproject.toml       — name = "agentix-claude-code"
├── default.nix          — Nix derivation: claude CLI + git
└── claude_code.py       — async def run(...) and RunResult
```

Flat single-file module, no `src/agentix/…` ceremony. The framework
only cares that the `agentix.namespace` entry point names a real
Python module:

```toml
[project.entry-points."agentix.namespace"]
claude_code = "claude_code"
```

Caller-side:

```python
import claude_code

await c.remote(claude_code.run, instruction="…", workdir="/testbed")
```

## Method surface

```python
async def run(
    instruction: str,
    *,
    workdir: str = "/testbed",
    timeout: float = 600,
    model: str | None = None,
    max_turns: int | None = None,
    env: dict[str, str] | None = None,
) -> RunResult
```

Returns `RunResult(exit_code, stdout, stderr)`. That's it — the
namespace's job ends when claude exits.

## Why no patch field?

Earlier versions returned `patch` by running `git add -A && git diff
--cached` inside `run()`. Pulled out: patch extraction is generic
"what changed in this workdir", which is not the agent's identity.
It applies equally to Claude Code, Aider, OpenHands, hand-written
edits, anything. Putting it on the agent namespace means every agent
recipe has to ship the same git plumbing.

Extract on the host instead:

```python
diff = await c.remote(
    bash.run,
    command=f"cd {workdir} && git add -A && git diff --cached --no-color",
)
patch = diff.stdout if diff.exit_code == 0 else ""
```

`bash.run` is the framework's built-in shell primitive. The bundle
image needs `git` on PATH (it usually does — most benchmarks rely on
it too); the agent namespace doesn't have to mediate.

## Building

```bash
agentix build claude-code -o claude-code:0.1.0
agentix deploy local --image claude-code:0.1.0
```

Typically bundled with bash + a benchmark:

```bash
agentix build bash files claude-code swebench -o cookbook:0.1.0
```

Pass API keys per call via `env={"ANTHROPIC_API_KEY": "..."}`. Don't
bake them into the image.
