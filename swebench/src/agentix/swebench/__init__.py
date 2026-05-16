"""SWE-bench Verified as an Agentix namespace.

Usage:

    from agentix import RuntimeClient, swebench, claude_code

    async with RuntimeClient(sandbox.runtime_url) as c:
        ids   = await c.remote(swebench.list_ids, limit=5)
        task  = await c.remote(swebench.get_task, instance_id=ids[0])
        result = await c.remote(
            claude_code.run, instruction=task.problem, workdir=task.workdir,
        )
        score = await c.remote(
            swebench.score, instance_id=task.instance_id, patch=result.patch,
        )
        print(score.passed, score.logs)

The namespace is module-shaped: `list_ids`, `get_task`, `score` are the
remote-callable surface; `Task` and `Score` are types callers import
for annotations.

This is a deliberately compact demonstration of the integration
pattern — it loads the dataset, checks out the repo, applies the
patch, runs the held-out tests. For full SWE-bench fidelity (Docker
sandboxes, environment setup commits, the official harness's edge
cases), see `pip install swebench` and call their evaluator from
`score` instead.
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any


SPLIT = "princeton-nlp/SWE-bench_Verified"
REPO_BASE = "https://github.com"

# Where to materialise repo checkouts. `score` always re-checkouts into
# a fresh subdir so the agent's mutations don't leak into the ground
# truth run.
WORKROOT = Path(os.environ.get("AGENTIX_UPLOAD_ROOT", "/tmp")) / "swebench"


@dataclass
class Task:
    instance_id: str
    problem: str
    workdir: str
    test_cmd: str
    fail_to_pass: list[str]
    pass_to_pass: list[str]


@dataclass
class Score:
    instance_id: str
    passed: bool
    fail_to_pass_resolved: list[str]
    pass_to_pass_kept: list[str]
    fail_to_pass_missing: list[str]
    pass_to_pass_broken: list[str]
    logs: str
    extras: dict[str, Any] = field(default_factory=dict)


async def list_ids(limit: int | None = None) -> list[str]:
    """Return the instance_ids in SWE-bench Verified."""
    ds = await asyncio.to_thread(_load_split)
    ids = [row["instance_id"] for row in ds]
    return ids[:limit] if limit else ids


async def get_task(instance_id: str) -> Task:
    """Fetch one instance, materialise its repo at base_commit."""
    rec = await asyncio.to_thread(_record_for, instance_id)
    workdir = await asyncio.to_thread(_checkout, rec, slot="agent")
    return Task(
        instance_id=rec["instance_id"],
        problem=rec["problem_statement"],
        workdir=str(workdir),
        test_cmd=_test_cmd(rec),
        fail_to_pass=_as_list(rec["FAIL_TO_PASS"]),
        pass_to_pass=_as_list(rec["PASS_TO_PASS"]),
    )


async def score(instance_id: str, patch: str, timeout: float = 1800) -> Score:
    """Apply model patch + held-out tests, run them, return pass/fail breakdown."""
    rec = await asyncio.to_thread(_record_for, instance_id)
    workdir = await asyncio.to_thread(_checkout, rec, slot="eval")

    await _apply_patch(workdir, patch)
    await _apply_patch(workdir, rec["test_patch"])

    proc = await asyncio.create_subprocess_shell(
        _test_cmd(rec),
        cwd=workdir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        logs = stdout.decode(errors="replace")
    except TimeoutError:
        proc.kill()
        await proc.communicate()
        logs = f"test command timed out after {timeout}s"

    ftp = _as_list(rec["FAIL_TO_PASS"])
    ptp = _as_list(rec["PASS_TO_PASS"])
    passing = _tests_in_log(logs, status="PASSED")
    failing = _tests_in_log(logs, status="FAILED")

    ftp_resolved = [t for t in ftp if t in passing]
    ftp_missing = [t for t in ftp if t not in passing]
    ptp_kept = [t for t in ptp if t in passing and t not in failing]
    ptp_broken = [t for t in ptp if t in failing]

    return Score(
        instance_id=rec["instance_id"],
        passed=not ftp_missing and not ptp_broken,
        fail_to_pass_resolved=ftp_resolved,
        pass_to_pass_kept=ptp_kept,
        fail_to_pass_missing=ftp_missing,
        pass_to_pass_broken=ptp_broken,
        logs=logs,
    )


@lru_cache(maxsize=1)
def _load_split() -> list[dict[str, Any]]:
    """Pull the Verified split from HF and cache it in memory.

    Worker process keeps the dataset resident — first call eats the
    HF download, subsequent calls reuse the in-memory list.
    """
    from datasets import load_dataset  # heavy import; defer until first call

    cache_dir = WORKROOT / ".hf-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    ds = load_dataset(SPLIT, split="test", cache_dir=str(cache_dir))
    return list(ds)


def _record_for(instance_id: str) -> dict[str, Any]:
    for row in _load_split():
        if row["instance_id"] == instance_id:
            return row
    raise KeyError(f"unknown SWE-bench instance: {instance_id!r}")


def _checkout(rec: dict[str, Any], *, slot: str) -> Path:
    """Materialise rec['repo']@base_commit at WORKROOT/<instance>/<slot>.

    `slot` separates the agent's workspace from the eval workspace so
    a buggy patch can't leak into the held-out test run.
    """
    dest = WORKROOT / rec["instance_id"] / slot
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"{REPO_BASE}/{rec['repo']}.git"
    _run(["git", "clone", "--quiet", url, str(dest)])
    _run(["git", "checkout", "--quiet", rec["base_commit"]], cwd=dest)
    return dest


async def _apply_patch(workdir: Path, patch: str) -> None:
    if not patch.strip():
        return
    proc = await asyncio.create_subprocess_exec(
        "git", "apply", "--allow-empty", "--whitespace=nowarn", "-",
        cwd=workdir,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate(patch.encode())
    if proc.returncode:
        raise RuntimeError(f"git apply failed: {stderr.decode(errors='replace')}")


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    import subprocess
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if res.returncode:
        raise RuntimeError(f"{' '.join(cmd)} failed: {res.stderr}")


def _test_cmd(rec: dict[str, Any]) -> str:
    """SWE-bench Verified records don't carry a uniform `test_cmd`;
    pytest with the union of FAIL_TO_PASS + PASS_TO_PASS tests is a
    reasonable default for the common case."""
    tests = _as_list(rec["FAIL_TO_PASS"]) + _as_list(rec["PASS_TO_PASS"])
    quoted = " ".join(_shell_quote(t) for t in tests)
    return f"python -m pytest -rN --tb=short -v {quoted}"


def _as_list(value: Any) -> list[str]:
    """Records sometimes carry FAIL_TO_PASS as a JSON-encoded string."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        import json
        return json.loads(value)
    return list(value)


_PYTEST_LINE = re.compile(r"^(?P<name>\S+)\s+(?P<status>PASSED|FAILED|ERROR|SKIPPED)\b", re.M)


def _tests_in_log(log: str, status: str) -> set[str]:
    return {m.group("name") for m in _PYTEST_LINE.finditer(log) if m.group("status") == status}


def _shell_quote(s: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_./:\-=\[\]]+", s):
        return s
    return "'" + s.replace("'", "'\\''") + "'"


def __getattr__(name: str) -> Iterable[str]:
    # Friendly error if a typo names a method that doesn't exist —
    # `from agentix.swebench import score` should resolve; everything
    # else lets Python raise the normal AttributeError.
    raise AttributeError(f"module 'agentix.swebench' has no attribute {name!r}")
