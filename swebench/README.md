# `swebench` — SWE-bench scoring as an Agentix namespace

Wraps the official [`swebench`](https://github.com/swe-bench/SWE-bench)
package's per-repo specs and grading.

## Surface

```python
async def score(
    *,
    instance: dict[str, Any],        # raw row from princeton-nlp/SWE-bench_Verified
    patch: str,
    setup_timeout: float = 1800,
    eval_timeout: float = 1800,
) -> Score   # resolved, patch_applied, fail_to_pass_resolved/missing,
             # pass_to_pass_kept/broken, logs
```

## Sandbox requirements

The bundle image must ship:

- `bash`, `git`, `curl`
- Miniconda at `/opt/miniconda3` (eval scripts `source` it to activate
  the per-instance conda env)

## Usage

```python
from datasets import load_dataset
import swebench

inst = dict(load_dataset("princeton-nlp/SWE-bench_Verified", split="test")[0])

s = await c.remote(swebench.score, instance=inst, patch=patch)
print("PASS" if s.resolved else "FAIL", s.fail_to_pass_missing)
```

## Build

```bash
agentix build swebench -o swebench:0.1.0
```
