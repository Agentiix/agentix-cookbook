# `agentix.swebench` — SWE-bench Verified as an Agentix namespace

A worked example of wrapping a benchmark/dataset as an Agentix
namespace. The pattern generalises to any "hand out instances, score
patches" benchmark (HumanEval, MLE-Bench, OSWorld, …).

## Layout

```
swebench/
├── pyproject.toml                   — name = "agentix-swebench"
└── src/agentix/swebench/__init__.py — list_ids, get_task, score
```

No `default.nix` here — the dataset is downloaded lazily from
HuggingFace on first call. For larger datasets you might prefer to
bake the records into the image via Nix; see "Where the data lives"
in the [framework docs](https://github.com/Agentiix/Agentix/blob/master/docs/integrate-dataset.mdx).

## Method surface

```python
async def list_ids(limit: int | None = None) -> list[str]: ...
async def get_task(instance_id: str) -> Task: ...
async def score(instance_id: str, patch: str, timeout: float = 1800) -> Score: ...
```

`get_task` materialises `rec.repo @ rec.base_commit` at
`$AGENTIX_UPLOAD_ROOT/swebench/<instance>/agent/` and returns the
problem statement + workdir path. The agent works there.

`score` re-materialises a **clean** copy at
`$AGENTIX_UPLOAD_ROOT/swebench/<instance>/eval/` — agent mutations
must not leak into the ground-truth run — applies the model patch
plus the held-out `test_patch`, then runs the FAIL_TO_PASS +
PASS_TO_PASS tests under pytest. The returned `Score` breaks down
which held-out tests now pass and whether any previously-passing
tests broke.

## Usage

```python
from agentix import RuntimeClient, swebench, claude_code

async with RuntimeClient(sandbox.runtime_url) as c:
    ids  = await c.remote(swebench.list_ids, limit=5)
    task = await c.remote(swebench.get_task, instance_id=ids[0])

    cc = await c.remote(
        claude_code.run,
        instruction=task.problem,
        workdir=task.workdir,
        env={"ANTHROPIC_API_KEY": api_key},
    )

    s = await c.remote(
        swebench.score, instance_id=task.instance_id, patch=cc.patch,
    )
    print("passed" if s.passed else "failed", s.fail_to_pass_missing)
```

## Scope of this recipe

This is a *compact demonstration* of the namespace pattern — it loads
the dataset, checks out the repo, applies the patch, runs the
held-out tests. For full SWE-bench fidelity:

- Each instance needs a specific Python toolchain (the
  `environment_setup_commit` + the repo's own setup). The recipe
  assumes the sandbox already has a workable interpreter and pytest;
  real eval pins the env per-instance.
- Some repos use unittest or nose instead of pytest. `_test_cmd`
  hardcodes pytest.
- Result parsing reads pytest's `-v` output. A more robust path
  shells out to the official `swebench` harness (`pip install
  swebench`) and lets it produce the report.

Drop in `swebench.harness.run_evaluation(...)` inside `score` when
you need the official numbers; the cookbook leaves it out to keep
the example dependency-light and the control flow visible.

## Building

```bash
agentix build swebench -o swebench:0.1.0
# Or, bundled with the agent:
agentix build bash files claude-code swebench -o cookbook:0.1.0
```
