# Agentix Cookbook

End-to-end examples of using [Agentix](https://github.com/Agentiix/Agentix)
in real workflows. Each example is its own buildable project under
`examples/`.

## Examples

| Example | What it does |
|---|---|
| [`examples/hello-agentix/`](./examples/hello-agentix) | Smallest end-to-end flow: `agentix build` a bundle, overlay it onto `python:3.13-slim`, `bash.run` remote, tear down. |
| [`examples/eval-cc-swe/`](./examples/eval-cc-swe) | Evaluate Claude Code on SWE-bench Verified — clone repo, run claude, score the patch. |

Each example is a self-contained Python project with its own
`pyproject.toml` + `default.nix` + `run.py`. Pick one, `cd` into it,
follow the README inside.

## Shape of a cookbook example

```
examples/<name>/
├── pyproject.toml          — `name = "<name>"`, deps include agentix-* plugins
├── default.nix             — OPTIONAL — Nix-pinned system binaries
├── README.md
├── run.py                  — host-side orchestrator
└── src/<name>/__init__.py  — sandbox-side async functions (your code)
```

Conventions:

* The example's module lives at `src/<example_name>/` — a normal
  Python package at your own import path. **Not** under `agentix.*`;
  that convention is only for reusable plugins.
* `agentix build .` from the example directory packages the project +
  its declared deps into one image. The framework auto-discovers any
  importable Python module on first dispatch — no entry-point
  declaration needed.

## License

MIT — see [LICENSE](./LICENSE).
