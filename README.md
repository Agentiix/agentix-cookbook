# Agentix Cookbook

Working namespace recipes for [Agentix](https://github.com/Agentiix/Agentix).
Each subdirectory is a standalone pip-installable wheel.

## Recipes

- [`claude-code/`](./claude-code) — **agentix-claude-code**. Wraps
  Anthropic's [Claude Code](https://docs.anthropic.com/claude/docs/claude-code)
  CLI as a typed namespace. Nix-pinned binary, per-call API key
  passthrough, exposes `claude_code.run(instruction, workdir, ...) -> RunResult`.
- [`swebench/`](./swebench) — **agentix-swebench**. Wraps the official
  [`swebench`](https://github.com/swe-bench/SWE-bench) package's
  `make_test_spec` + `get_eval_report`. Exposes one method:
  `swebench.score(instance, patch) -> Score`.

## End-to-end example

A SWE-bench Verified rollout, composed from three namespaces:

```python
from datasets import load_dataset
from agentix import RuntimeClient, bash, claude_code, swebench

inst = dict(load_dataset("princeton-nlp/SWE-bench_Verified", split="test")[0])

async with RuntimeClient(sandbox.runtime_url) as c:
    await c.remote(
        bash.run,
        command=(
            f"git clone https://github.com/{inst['repo']}.git /testbed && "
            f"cd /testbed && git checkout {inst['base_commit']}"
        ),
    )
    cc = await c.remote(
        claude_code.run,
        instruction=inst["problem_statement"],
        workdir="/testbed",
        env={"ANTHROPIC_API_KEY": api_key},
    )
    diff = await c.remote(
        bash.run, command="cd /testbed && git add -A && git diff --cached",
    )
    s = await c.remote(swebench.score, instance=inst, patch=diff.stdout)
```

Full version in [`examples/swebench_with_claude_code.py`](./examples/swebench_with_claude_code.py).

## Install, build, run

```bash
pip install ./claude-code ./swebench
agentix build bash files claude-code swebench -o cookbook:0.1.0
agentix deploy local --image cookbook:0.1.0

python examples/swebench_with_claude_code.py --limit 5
```

## Sandbox requirements

The bundle image needs:

- `bash`, `git`, `curl` on PATH
- Miniconda at `/opt/miniconda3` (the SWE-bench eval scripts source it
  to activate per-instance conda envs)

## License

MIT — see [LICENSE](./LICENSE).
