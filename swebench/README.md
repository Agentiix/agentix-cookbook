# `swebench` — SWE-bench scoring as an Agentix namespace

Wraps the official [SWE-bench](https://github.com/swe-bench/SWE-bench)
package as a remote-callable Agentix namespace. The recipe takes the
parts of swebench that genuinely need to be reused — per-repo test
specs, log parsers, the grading function — and writes the async
orchestration in our framework's idiom.

## Surface

ONE method:

```python
async def score(
    *,
    instance: dict[str, Any],        # raw row from princeton-nlp/SWE-bench_Verified
    patch: str,                      # model patch to evaluate
    setup_timeout: float = 1800,
    eval_timeout: float = 1800,
) -> Score
```

Returns `Score(resolved, patch_applied, fail_to_pass_resolved,
fail_to_pass_missing, pass_to_pass_kept, pass_to_pass_broken, logs)`.

`resolved` and `patch_applied` come straight from the official
`get_eval_report`. Test breakdowns are pulled from that same report
under `tests_status`.

## What's reused vs reimplemented

| From `swebench` | Used for |
|---|---|
| `make_test_spec(instance)` | per-repo test command, conda env script, eval script with START/END markers |
| `MAP_REPO_TO_PARSER[repo]` | log parsing (invoked indirectly via `get_eval_report`) |
| `get_eval_report` | grading: which FAIL_TO_PASS resolved, which PASS_TO_PASS broke, did the patch apply |
| Marker constants (`APPLY_PATCH_PASS`, `TESTS_TIMEOUT`, etc.) | log signal the official parser expects |

| Written here | Why |
|---|---|
| The score() coroutine | Async, namespace-shaped — matches Agentix's wire layer instead of swebench's `run_evaluation` Docker orchestrator |
| Per-step subprocess driver | Smaller surface, clear timeout boundaries, no Docker-in-Docker |

The swebench harness's full `run_evaluation` builds per-instance
Docker images and runs each container itself. We can't (and
shouldn't) do that from inside an already-sandboxed Agentix runtime;
this recipe sets the env up in the sandbox itself and uses the
package's grading directly.

## Sandbox requirements

The eval scripts that `make_test_spec` generates assume:

- `bash`, `git`, `curl` on PATH
- `/opt/miniconda3/` with `conda` available — the scripts do
  `source /opt/miniconda3/bin/activate testbed` to enter the
  per-instance env they create

Bake these into the bundle image's Dockerfile (the framework's
runtime image is python:3.11-slim; you'll need to layer miniconda
on top yourself). Or point the bundle at SWE-bench's own
per-instance images for full reproducibility.

## Layout

```
swebench/
├── pyproject.toml      — depends on `swebench>=4.0`
└── swebench.py         — async def score(...)
```

## Usage

```python
from datasets import load_dataset
from agentix import RuntimeClient
import bash, claude_code, swebench

inst = dict(load_dataset("princeton-nlp/SWE-bench_Verified", split="test")[0])

async with RuntimeClient(sandbox.runtime_url) as c:
    # 1. Materialise the agent's workdir (the agent works in /testbed too,
    #    but score() resets it — so do the agent run first).
    await c.remote(
        bash.run,
        command=(
            f"rm -rf /testbed && "
            f"git clone https://github.com/{inst['repo']}.git /testbed && "
            f"cd /testbed && git checkout {inst['base_commit']}"
        ),
    )

    # 2. Run the agent.
    cc = await c.remote(
        claude_code.run, instruction=inst["problem_statement"], workdir="/testbed",
        env={"ANTHROPIC_API_KEY": api_key},
    )

    # 3. Score. The recipe re-clones /testbed and rebuilds the conda env
    #    so the agent's state can't leak into the eval.
    s = await c.remote(swebench.score, instance=inst, patch=cc.patch)
    print("PASS" if s.resolved else "FAIL", s.fail_to_pass_missing, s.pass_to_pass_broken)
```

## Building

```bash
agentix build swebench -o swebench:0.1.0
# Or, bundled:
agentix build bash files claude-code swebench -o cookbook:0.1.0
```
