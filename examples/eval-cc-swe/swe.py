"""Sandbox-side: run the SWE-bench Verified scorer against a patch.

Host orchestrator calls `c.remote(swe.score, instance=..., patch=...)`.
Wraps `make_test_spec` + `get_eval_report` from the upstream `swebench`
package; each instance gets its own conda env under
`/opt/miniconda3` (the runtime image must ship miniconda there).
"""

from __future__ import annotations

import asyncio
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WORKROOT = Path(os.environ.get("AGENTIX_UPLOAD_ROOT", "/tmp")) / ".cache" / "swebench-eval"
TESTBED = "/testbed"
LOG_FILE = "test_output.log"


@dataclass
class Score:
    resolved: bool
    patch_applied: bool
    fail_to_pass_resolved: list[str]
    fail_to_pass_missing: list[str]
    pass_to_pass_kept: list[str]
    pass_to_pass_broken: list[str]
    logs: str


async def score(
    *,
    instance: dict[str, Any],
    patch: str,
    setup_timeout: float = 1800,
    eval_timeout: float = 1800,
) -> Score:
    """Run the official SWE-bench evaluation for `instance` against `patch`."""
    from swebench.harness.constants import (
        APPLY_PATCH_FAIL,
        APPLY_PATCH_PASS,
        KEY_INSTANCE_ID,
        KEY_MODEL,
        KEY_PREDICTION,
    )
    from swebench.harness.grading import get_eval_report
    from swebench.harness.test_spec.test_spec import make_test_spec

    spec = make_test_spec(instance)
    workroot = WORKROOT / spec.instance_id
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)

    log_path = workroot / LOG_FILE

    # 1. Reset /testbed: clone repo at base_commit, create per-instance conda env.
    setup_log = await _run_script(
        workroot / "setup.sh",
        ["#!/bin/bash", "set -uxo pipefail", f"rm -rf {TESTBED}",
         *spec.repo_script_list, *spec.env_script_list],
        timeout=setup_timeout,
    )

    # 2. Apply the model patch under the testbed's conda env. Emit the
    #    official APPLY_PATCH_PASS / APPLY_PATCH_FAIL markers so the
    #    grading function can tell whether the patch took.
    (workroot / "model.patch").write_text(patch or "")
    apply_log = await _run_script(
        workroot / "apply.sh",
        ["#!/bin/bash", "set -uxo pipefail",
         "source /opt/miniconda3/bin/activate testbed",
         f"cd {TESTBED}",
         f"if git apply --allow-empty --whitespace=nowarn {workroot}/model.patch; then",
         f"  echo '{APPLY_PATCH_PASS}'",
         "else",
         f"  echo '{APPLY_PATCH_FAIL}'",
         "fi"],
        timeout=300,
    )

    # 3. Run the official eval script (applies test_patch + runs test
    #    cmd with START/END markers around stdout).
    eval_log = await _run_script(
        workroot / "eval.sh",
        spec.eval_script.splitlines(),
        timeout=eval_timeout,
    )

    log_path.write_text(setup_log + apply_log + eval_log)

    # 4. Grade with the official report function.
    report = get_eval_report(
        test_spec=spec,
        prediction={
            KEY_INSTANCE_ID: spec.instance_id,
            KEY_MODEL: "eval-cc-swe",
            KEY_PREDICTION: patch,
        },
        test_log_path=str(log_path),
        include_tests_status=True,
    )
    entry = report[spec.instance_id]
    tests = entry.get("tests_status", {})
    ftp = tests.get("FAIL_TO_PASS", {"success": [], "failure": []})
    ptp = tests.get("PASS_TO_PASS", {"success": [], "failure": []})

    return Score(
        resolved=entry.get("resolved", False),
        patch_applied=entry.get("patch_successfully_applied", False),
        fail_to_pass_resolved=list(ftp.get("success", [])),
        fail_to_pass_missing=list(ftp.get("failure", [])),
        pass_to_pass_kept=list(ptp.get("success", [])),
        pass_to_pass_broken=list(ptp.get("failure", [])),
        logs=log_path.read_text(),
    )


async def _run_script(path: Path, lines: list[str], *, timeout: float) -> str:
    """Write `lines` to `path`, chmod +x, run it, return combined stdout+stderr."""
    path.write_text("\n".join(lines) + "\n")
    path.chmod(0o755)
    proc = await asyncio.create_subprocess_exec(
        "bash", str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return out.decode(errors="replace")
    except TimeoutError:
        proc.kill()
        await proc.communicate()
        from swebench.harness.constants import TESTS_TIMEOUT
        return f"{TESTS_TIMEOUT}\nscript {path.name} timed out after {timeout}s\n"
