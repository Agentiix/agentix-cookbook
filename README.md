<div align="center">

# Agentix Cookbook

**Worked examples of integrating agents and datasets with [Agentix](https://github.com/Agentiix/Agentix).**

</div>

## What this is

Each subdirectory is a self-contained, pip-installable Agentix namespace
distribution. Read the source, copy it as a starting point, or install
the wheel directly.

```bash
pip install ./claude-code     # claude_code agent namespace
pip install ./swebench        # swebench scorer namespace
```

Then bundle + deploy:

```bash
agentix build bash files claude-code swebench -o cookbook:0.1.0
agentix deploy local --image cookbook:0.1.0
```

## Recipes

| Path | Namespace | What it does |
|---|---|---|
| [`claude-code/`](./claude-code) | `claude_code` | Wrap an agent CLI: Nix-pinned binary, subprocess exec, patch extraction. |
| [`swebench/`](./swebench) | `swebench` | Score a SWE-bench patch: apply model + held-out tests, run, report. |

## On layout

These recipes are **flat single-file modules** — no `src/agentix/…`
nesting. The framework's `agentix.namespace` entry point names a
module by its import path; that import path can be anything. The
framework's own primitives (`bash`, `files`) use `agentix.<short>`
for unified imports across distributions; cookbook recipes use plain
top-level module names because the ceremony to land under `agentix.`
isn't worth it for a one-off integration. Both layouts are first-class.

## End-to-end

[`examples/swebench_with_claude_code.py`](./examples/swebench_with_claude_code.py)
loads one SWE-bench Verified instance, materialises the repo with
`bash`, hands the issue to Claude Code, scores the resulting patch.

```bash
python examples/swebench_with_claude_code.py            # one instance
python examples/swebench_with_claude_code.py --limit 5  # five
```

## License

MIT — see [LICENSE](./LICENSE).
