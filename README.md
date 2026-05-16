<div align="center">

# Agentix Cookbook

**Worked examples of integrating agents and datasets with [Agentix](https://github.com/Agentiix/Agentix).**

</div>

## What this is

Each subdirectory is a self-contained, pip-installable Agentix namespace
distribution. Read the source, copy it as a starting point for your own
integration, or install the wheel directly.

```bash
pip install ./claude-code     # claude_code agent namespace
pip install ./swebench        # SWE-bench dataset namespace
```

Then bundle and deploy in one step:

```bash
agentix build bash files claude-code swebench -o cookbook:0.1.0
agentix deploy local --image cookbook:0.1.0
```

## Recipes

| Path | Namespace | What it shows |
|---|---|---|
| [`claude-code/`](./claude-code) | `agentix.claude_code` | Wrap an agent CLI binary (Claude Code) as a namespace — Nix-pinned binary, subprocess exec, patch extraction. |
| [`swebench/`](./swebench) | `agentix.swebench` | Wrap a benchmark (SWE-bench Verified) as a namespace — instance fetch, repo checkout, patch scoring. |

## End-to-end

[`examples/swebench_with_claude_code.py`](./examples/swebench_with_claude_code.py)
puts both recipes together: pull a SWE-bench task, hand the problem to
Claude Code, score the resulting patch. Run it against a local
sandbox:

```bash
python examples/swebench_with_claude_code.py
```

## Conventions

These recipes follow the
[Agentix framework conventions](https://github.com/Agentiix/Agentix/blob/master/CLAUDE.md):
each recipe is a normal Python project that contributes an
`agentix.namespace` entry point and ships its source under
`src/agentix/<short>/`. Namespaces are module-shaped — top-level
async functions are the remote-callable surface; types and constants
are regular Python imports.

## License

MIT — see [LICENSE](./LICENSE).
