# eval-cc-swe — evaluate Claude Code on SWE-bench Verified

End-to-end example: spin up a sandbox, run Claude Code against each
SWE-bench Verified instance, apply the resulting patch, score it with
the official harness.

```
examples/eval-cc-swe/
├── pyproject.toml                       — project + deps
├── default.nix                          — claude CLI + git (Nix-pinned)
├── README.md
├── run.py                               — host orchestrator
└── src/eval_cc_swe/__init__.py          — sandbox-side: run_claude + score
```

## Architecture

```
                  host                              sandbox
       ┌────────────────────────┐        ┌────────────────────────┐
       │ run.py                 │        │  worker subprocess     │
       │   load_dataset()       │        │    eval_cc_swe.run_claude
       │   c.remote(bash.run, …)│ ─────► │    eval_cc_swe.score    │
       │   c.remote(run_claude, …)       │    bash.run (from       │
       │   c.remote(score, …)   │        │    agentix-runtime-basic)
       └────────────────────────┘        └────────────────────────┘
```

`run_claude` and `score` are regular Python async functions in the
`eval_cc_swe` module. They become RPC-dispatchable simply by being
imported on the caller side — `c.remote(run_claude, ...)` reads
`run_claude.__module__` (`eval_cc_swe`) and the sandbox-side
multiplexer auto-registers the module on first dispatch.

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
# host-side: enables `from eval_cc_swe import …` for typed dispatch
pip install -e .

# package the project + every declared dep into one image
agentix build . -o eval-cc-swe:0.1.0

# run
export ANTHROPIC_API_KEY=sk-…
python run.py --limit 5
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

## What this example demonstrates

* **One project = one bundle.** The pyproject's `[project].dependencies`
  is the bundle's plugin set; `agentix build .` resolves it and ships
  one image.
* **No `agentix.*` import path required for user code.** `eval_cc_swe`
  is just a regular Python module — the framework dispatches by
  `fn.__module__`, not by entry-point declaration.
* **Inline composition.** `run.py` mixes `bash.run` (from
  `agentix-runtime-basic`) with `run_claude` and `score` (this project)
  freely. All three live in the same `/nix/runtime/` venv in the
  bundle image; `from agentix import bash` works inside any worker.
* **Nix for hermetic system binaries.** The pinned `claude` CLI lives
  in `default.nix`; the bundle build symlinks it into
  `/nix/runtime/bin/claude` so every worker picks it up via PATH.
