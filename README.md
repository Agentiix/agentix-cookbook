<div align="center">

# Agentix Cookbook

**Working recipes for [Agentix](https://github.com/Agentiix/Agentix).**
Copy-paste-ready namespaces — Claude Code agent, SWE-bench scorer —
that you can pip-install today.

</div>

## End-to-end in 8 lines

```python
from datasets import load_dataset
from agentix import RuntimeClient, bash, claude_code, swebench

inst = dict(load_dataset("princeton-nlp/SWE-bench_Verified", split="test")[0])

async with RuntimeClient(sandbox.runtime_url) as c:
    await c.remote(bash.run, command=f"git clone https://github.com/{inst['repo']}.git /testbed && cd /testbed && git checkout {inst['base_commit']}")
    cc = await c.remote(claude_code.run, instruction=inst["problem_statement"], workdir="/testbed")
    diff = await c.remote(bash.run, command="cd /testbed && git add -A && git diff --cached")
    s = await c.remote(swebench.score, instance=inst, patch=diff.stdout)
```

## Recipes

| Path | Namespace | What it does |
|---|---|---|
| [`claude-code/`](./claude-code) | `claude_code` | Wrap the Claude Code CLI — Nix-pinned binary, subprocess exec, typed return. |
| [`swebench/`](./swebench) | `swebench` | Score a SWE-bench patch via the official package's specs + grading. |

## Install, build, run

```bash
pip install ./claude-code ./swebench
agentix build bash files claude-code swebench -o cookbook:0.1.0
agentix deploy local --image cookbook:0.1.0

python examples/swebench_with_claude_code.py            # one instance
python examples/swebench_with_claude_code.py --limit 5  # five
```

## License

MIT — see [LICENSE](./LICENSE).
