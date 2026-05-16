# `claude_code` — Claude Code as an Agentix namespace

A worked example of wrapping an agent CLI binary. The pattern
generalises to any single-binary agent (Aider, Codex, …) — copy
this directory, swap the Nix derivation's `src`, adjust the argv.

## Layout

```
claude-code/
├── pyproject.toml       — name = "agentix-claude-code"
├── default.nix          — Nix derivation: claude CLI + git
└── claude_code.py       — async def run(...) and types
```

The recipe is a flat, single-file module — no `src/agentix/…`
ceremony. The framework only cares that the `agentix.namespace`
entry point names a real Python module:

```toml
[project.entry-points."agentix.namespace"]
claude_code = "claude_code"
```

Caller-side:

```python
import claude_code

await c.remote(claude_code.run, instruction="…", workdir="/testbed")
```

(If you want `from agentix import claude_code` instead, put the source
under `src/agentix/claude_code/` and point the entry-point value at
`agentix.claude_code`. Both shapes are valid; the flat one is simpler.)

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

Returns `RunResult(exit_code, stdout, stderr, patch)`. `patch` is the
unified diff of all changes the agent made to `workdir`, computed via
`git add -A && git diff --cached` after `claude` exits.

## Building

```bash
agentix build claude-code -o claude-code:0.1.0
agentix deploy local --image claude-code:0.1.0
```

Typically bundled with other namespaces:

```bash
agentix build bash files claude-code swebench -o cookbook:0.1.0
```

Pass API keys per call via `env={"ANTHROPIC_API_KEY": "..."}`. Don't
bake them into the image.
