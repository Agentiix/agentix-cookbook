# eval-cc-swe — evaluate Claude Code on SWE-bench Verified

End-to-end example: spin up a sandbox, run Claude Code against each
SWE-bench Verified instance, apply the resulting patch, score it with
the official harness.

```
examples/eval-cc-swe/
├── pyproject.toml     — project + deps
├── default.nix        — claude CLI + git (Nix-pinned)
├── README.md
├── cc.py              — sandbox: `cc.run(instruction, …)` → claude CLI
├── swe.py             — sandbox: `swe.score(instance, patch)` → SWE-bench harness
└── runner.py          — host: orchestrator (`python -m runner …`)
```

`cc` and `swe` are sandbox-side dispatch targets (regular Python
modules — no `agentix.*` import path needed). `runner` is the
host-side orchestrator that wires them together.

## Architecture

```
                  host                              sandbox
       ┌────────────────────────┐        ┌────────────────────────┐
       │ python -m runner       │        │  worker processes      │
       │   c.remote(bash.run,…) │ ─────► │    bash.run            │
       │   c.remote(cc.run, …)  │        │    cc.run              │
       │   c.remote(swe.score,…)│        │    swe.score           │
       └────────────────────────┘        └────────────────────────┘
```

Routing is by `fn.__module__`: `cc.run` lands on a worker for module
`cc`, `swe.score` on a worker for `swe`. The framework auto-registers
each on first dispatch — no entry-point declaration needed.

## One-time setup

The bundle extends `agentix/runtime:<framework-version>`. Build the
base image once from the sibling repo:

```bash
docker build -t agentix/runtime:0.1.0 \
    -f ../../../Agentix-Runtime-Basic/runtime/Dockerfile .
```

The SWE-bench harness needs miniconda at `/opt/miniconda3` inside the
sandbox to set up per-instance conda envs. Either bake that into your
runtime image or extend `default.nix` here.

## Install, build, run

```bash
# host-side: enables `from cc import run`, `from swe import score`,
# `from runner import main` for typed dispatch
pip install -e .

# package the project + every declared dep into one image
agentix build . -o eval-cc-swe:0.1.0

# run
export ANTHROPIC_API_KEY=sk-…
python -m runner --limit 5
```

## Output

```
sandbox up: http://127.0.0.1:42337
[django__django-11099] cloning django/django@d4b3eed40d
[django__django-11099] running claude
[django__django-11099] claude exit=0 patch_bytes=412
[django__django-11099] PASS  patch_applied=True  resolved=2/2  regressions=0
[django__django-13447] …
```
