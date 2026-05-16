# `swebench` — SWE-bench Verified scoring as an Agentix namespace

A worked example of wrapping a benchmark's *scorer* as a namespace.
The pattern generalises to any "given a patch + instance metadata,
did it pass?" eval.

## Surface

ONE method:

```python
async def score(
    *,
    repo: str,                   # "django/django"
    base_commit: str,            # commit hash
    patch: str,                  # the model's patch
    test_patch: str,             # the dataset's held-out test patch
    fail_to_pass: list[str],     # tests that should pass after the fix
    pass_to_pass: list[str],     # tests that should still pass
    test_cmd: str | None = None, # defaults to pytest on FTP+PTP
    timeout: float = 1800,
) -> Score
```

Returns
`Score(passed, fail_to_pass_resolved, fail_to_pass_missing, pass_to_pass_broken, logs)`.

## Layout

```
swebench/
├── pyproject.toml      — name = "agentix-swebench"
└── swebench.py         — async def score(...)
```

Flat single-file module, just like `claude-code/`.

## Why only `score`?

- **Dataset enumeration is host-side.** The caller already wants to
  pick which instances to run, in what order, with what filters —
  `datasets.load_dataset(...)` in their orchestration script does this
  better than a thin remote wrapper around it.
- **Repo materialisation is the agent's setup, not the scorer's.**
  Use the `bash` namespace (`git clone …`) or let the agent clone the
  repo itself as part of its prompt. The scorer never has to mediate
  the agent's workspace.
- **Score is what only the scorer can do.** Applying the held-out
  test patch + running the right tests + parsing the right output is
  the work that belongs *inside* the sandbox, next to the test runner.

The namespace owns one job and does it.

## Usage

```python
from datasets import load_dataset
from agentix import RuntimeClient
import bash, claude_code, swebench

ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
inst = ds[0]

async with RuntimeClient(sandbox.runtime_url) as c:
    # 1. Set up the agent's workdir
    await c.remote(
        bash.run,
        command=(
            f"rm -rf /testbed && "
            f"git clone https://github.com/{inst['repo']}.git /testbed && "
            f"cd /testbed && git checkout {inst['base_commit']}"
        ),
    )

    # 2. Run the agent
    cc = await c.remote(
        claude_code.run,
        instruction=inst["problem_statement"],
        workdir="/testbed",
        env={"ANTHROPIC_API_KEY": api_key},
    )

    # 3. Score
    s = await c.remote(
        swebench.score,
        repo=inst["repo"],
        base_commit=inst["base_commit"],
        patch=cc.patch,
        test_patch=inst["test_patch"],
        fail_to_pass=inst["FAIL_TO_PASS"],
        pass_to_pass=inst["PASS_TO_PASS"],
    )
    print("PASS" if s.passed else "FAIL", s.fail_to_pass_missing)
```

## Scope

The default pytest invocation works for the pytest-using majority of
SWE-bench Verified. Django, nose, tox-wrapped, or instance-specific
build steps need an explicit `test_cmd` from the caller (or a pre-
built per-instance environment). For full reproducibility numbers,
delegate to `swebench.harness.run_evaluation` from inside `score`
rather than relying on this recipe's compact pytest path.

## Building

```bash
agentix build swebench -o swebench:0.1.0
# Or, bundled with the agent + bash:
agentix build bash files claude-code swebench -o cookbook:0.1.0
```
