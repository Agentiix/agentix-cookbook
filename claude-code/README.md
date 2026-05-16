# `agentix.claude_code` — Claude Code as an Agentix namespace

A worked example of wrapping an agent CLI binary as an Agentix
namespace. The pattern generalises to any single-binary agent
(Aider, OpenHands, Codex, …) — copy this directory, swap the Nix
derivation's `src`, and adjust the argv.

## Layout

```
claude-code/
├── pyproject.toml                       — name = "agentix-claude-code"
├── default.nix                          — Nix derivation: claude CLI + git
└── src/agentix/claude_code/__init__.py  — async def run(...) and types
```

`pyproject.toml` declares the entry point:

```toml
[project.entry-points."agentix.namespace"]
claude_code = "agentix.claude_code"
```

`pip install ./claude-code` makes `from agentix import claude_code`
work caller-side; on the sandbox side, `agentix build claude-code …`
runs the Nix derivation and lays `bin/claude` + `bin/git` into the
namespace's `/nix/claude_code/bin/` so user code can invoke them by
bare name.

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
`git add -A && git diff --cached` after `claude` exits — works whether
the agent committed, staged, or just modified files in place.

## Usage

```python
from agentix import RuntimeClient, claude_code

async with RuntimeClient(sandbox.runtime_url) as c:
    result = await c.remote(
        claude_code.run,
        instruction="Fix the failing test in tests/test_foo.py",
        workdir="/testbed",
        env={"ANTHROPIC_API_KEY": api_key},
    )
    print(result.patch)
```

Pass API keys through `env=` per call. Don't bake them into the image —
the bundle is shareable across runs and (often) across users.

## Building

```bash
agentix build claude-code -o claude-code:0.1.0
agentix deploy local --image claude-code:0.1.0
```

Bundle it with other namespaces — typically `bash`, `files`, and a
dataset — in a single `agentix build` invocation:

```bash
agentix build bash files claude-code swebench -o cookbook:0.1.0
```

## Extending

- **Streaming output.** Add `async def run_stream(...) -> AsyncIterator[Event]:`
  next to `run`. Yield dataclasses for each `claude --output-format
  stream-json` event; callers iterate with `async for`.
- **Other agents.** The whole recipe is "wrap a CLI". For Aider, swap
  the Nix `src` (PyPI wheel or pinned commit), change argv to
  `["aider", "--message", instruction, ...]`, and keep the same patch
  extraction.
