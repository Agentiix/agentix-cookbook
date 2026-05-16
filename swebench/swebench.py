"""SWE-bench Verified scoring as an Agentix namespace.

ONE method: `score`. Apply the model patch + the dataset's held-out
test patch to the target repo, run the relevant tests, return what
passed / failed / regressed. The dataset is the caller's concern —
load it with `datasets`, iterate, pass the instance fields to
`score` per call.

    from datasets import load_dataset
    from agentix import RuntimeClient
    import swebench

    ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
    inst = ds[0]

    async with RuntimeClient(sandbox.runtime_url) as c:
        s = await c.remote(
            swebench.score,
            repo=inst["repo"],
            base_commit=inst["base_commit"],
            patch=agent_patch,
            test_patch=inst["test_patch"],
            fail_to_pass=inst["FAIL_TO_PASS"],
            pass_to_pass=inst["PASS_TO_PASS"],
        )
        print(s.passed, s.fail_to_pass_missing)

Repo materialisation for the agent is also caller-side — use `bash`
to clone or have the agent clone itself. Keeping the namespace
focused on scoring means it never has to manage agent workspaces or
mediate dataset access.
"""

from __future__ import annotations

import asyncio
import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


WORKROOT = Path(os.environ.get("AGENTIX_UPLOAD_ROOT", "/tmp")) / ".cache" / "swebench-eval"


@dataclass
class Score:
    passed: bool
    fail_to_pass_resolved: list[str]
    fail_to_pass_missing: list[str]
    pass_to_pass_broken: list[str]
    logs: str


async def score(
    *,
    repo: str,
    base_commit: str,
    patch: str,
    test_patch: str,
    fail_to_pass: list[str],
    pass_to_pass: list[str],
    test_cmd: str | None = None,
    timeout: float = 1800,
) -> Score:
    """Apply `patch` + `test_patch` to `repo`@`base_commit` and run the tests.

    The eval workdir is fresh per call — never trusts external state.
    Cleaned up on exit (success or failure).

    `test_cmd` defaults to a pytest invocation on the union of the
    expected tests. Repos whose suites don't speak pytest (Django,
    nose, tox-wrapped, …) require an explicit `test_cmd`; the cookbook
    leaves that mapping to the caller to keep this recipe small. For
    full per-repo fidelity, delegate to `swebench.harness.run_evaluation`.
    """
    workdir = await asyncio.to_thread(_checkout, repo, base_commit)
    try:
        await _apply(workdir, patch)
        await _apply(workdir, test_patch)
        cmd = test_cmd or _pytest_for(fail_to_pass + pass_to_pass)
        logs = await _run(cmd, workdir, timeout)
        passed_tests, failed_tests = _parse_pytest(logs)
        missing = [t for t in fail_to_pass if t not in passed_tests]
        broken = [t for t in pass_to_pass if t in failed_tests]
        return Score(
            passed=not missing and not broken,
            fail_to_pass_resolved=[t for t in fail_to_pass if t in passed_tests],
            fail_to_pass_missing=missing,
            pass_to_pass_broken=broken,
            logs=logs,
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _checkout(repo: str, base_commit: str) -> Path:
    """Clone `repo` at `base_commit` into a fresh dir."""
    dest = WORKROOT / f"{repo.replace('/', '__')}-{base_commit[:12]}"
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--quiet", f"https://github.com/{repo}.git", str(dest)],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "checkout", "--quiet", base_commit],
        cwd=dest, check=True, capture_output=True,
    )
    return dest


async def _apply(workdir: Path, patch: str) -> None:
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


async def _run(cmd: str, cwd: Path, timeout: float) -> str:
    proc = await asyncio.create_subprocess_shell(
        cmd, cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return out.decode(errors="replace")
    except TimeoutError:
        proc.kill()
        await proc.communicate()
        return f"<test command timed out after {timeout}s>"


def _pytest_for(tests: list[str]) -> str:
    return "python -m pytest -rN --tb=short -v " + " ".join(shlex.quote(t) for t in tests)


_PYTEST_LINE = re.compile(r"^(?P<name>\S+)\s+(?P<status>PASSED|FAILED|ERROR)\b", re.M)


def _parse_pytest(log: str) -> tuple[set[str], set[str]]:
    passed, failed = set(), set()
    for m in _PYTEST_LINE.finditer(log):
        (passed if m["status"] == "PASSED" else failed).add(m["name"])
    return passed, failed
