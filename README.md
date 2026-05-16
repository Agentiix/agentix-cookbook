<div align="center">

# Agentix Cookbook

Worked examples for [Agentix](https://github.com/Agentiix/Agentix).

</div>

## Recipes

| Path | Namespace | What it does |
|---|---|---|
| [`claude-code/`](./claude-code) | `claude_code` | Wrap the Claude Code CLI as a namespace. |
| [`swebench/`](./swebench) | `swebench` | Score a SWE-bench patch via the official package. |

## Install + build + deploy

```bash
pip install ./claude-code ./swebench
agentix build bash files claude-code swebench -o cookbook:0.1.0
agentix deploy local --image cookbook:0.1.0
```

## End-to-end

```bash
python examples/swebench_with_claude_code.py            # one instance
python examples/swebench_with_claude_code.py --limit 5  # five
```

## License

MIT — see [LICENSE](./LICENSE).
