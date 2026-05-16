# `claude_code` — Claude Code as an Agentix namespace

## Layout

```
claude-code/
├── pyproject.toml
├── default.nix          — claude CLI + git
└── claude_code.py
```

## Surface

```python
async def run(
    instruction: str,
    *,
    workdir: str = "/testbed",
    timeout: float = 600,
    model: str | None = None,
    max_turns: int | None = None,
    env: dict[str, str] | None = None,
) -> RunResult                # exit_code, stdout, stderr
```

## Usage

```python
import claude_code, bash

r = await c.remote(
    claude_code.run,
    instruction="Fix tests/test_foo.py",
    workdir="/testbed",
    env={"ANTHROPIC_API_KEY": api_key},
)

diff = await c.remote(
    bash.run,
    command=f"cd /testbed && git add -A && git diff --cached --no-color",
)
patch = diff.stdout
```

## Build

```bash
agentix build claude-code -o claude-code:0.1.0
```
