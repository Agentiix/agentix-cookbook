# hello-agentix — smallest end-to-end Agentix flow

Build a runtime bundle, mount it onto a task image at sandbox-create
time, and remote-call `bash.run` inside the sandbox.

```
examples/hello-agentix/
├── pyproject.toml          — declares agentixx + agentix-runtime-basic + agentix-deployment-docker
├── README.md
├── run.py                  — host: create sandbox, call bash.run, tear down
└── src/hello_agentix/__init__.py   — placeholder (would hold your sandbox-side funcs)
```

## What it shows

The two-image model:

- **`runtime_image`** = the Agentix bundle from `agentix build`.
  Generic and reusable: holds Python + agentixx + agentix-runtime-basic
  + all transitive deps, under `/nix/store/...` with libc vendored.
- **`image`** = a task-specific base. Here we use `python:3.13-slim`,
  but any Linux image works (Alpine, RHEL, a SWE-bench task image).
  Distros differ; the runtime doesn't care because nothing in it links
  against the task image's libc.

`DockerDeployment` overlays the runtime's `/nix` onto the task image
at `docker run` time, then starts the `agentix-server` entrypoint
inside the task container.

## Install + build

```bash
cd examples/hello-agentix

# Host-side venv with the framework + deployment backend
uv sync

# Bundle the project + its deps into a runtime image
uv run agentix build . --name hello-agentix
# → docker images now has hello-agentix:0.1.0
```

`agentix build` reads `pyproject.toml` + `uv.lock`, runs `uv2nix` to
produce a Nix derivation for every Python dep, discovers each plugin's
`default.nix` (`agentix-runtime-basic` ships one for `bash` + one for
`files`), and emits a `streamLayeredImage` tarball that gets loaded
into Docker.

## Run

```bash
uv run python run.py
```

Expected output:

```
sandbox up at http://localhost:33803
exit=0 stdout='hello from Linux <kernel> ... GNU/Linux\n'
```

The first run also creates a stopped "carrier" container named
`agentix-runtime-<hash>` — it owns the runtime image's `/nix` volume so
subsequent sandboxes share it via `--volumes-from`. Stopped containers
cost only metadata; one per distinct `runtime_image` is enough.

## Tear down

`session(...)` deletes the sandbox container on exit. The carrier
persists between runs for reuse. To remove it:

```bash
docker ps -a --filter "name=agentix-runtime-" -q | xargs -r docker rm
```

## Extend

- Swap the task `image` for any Linux container — Alpine, Debian,
  Ubuntu, RHEL, a SWE-bench task image. The runtime overlay is
  distro-independent.
- Add a sandbox-side function in `src/hello_agentix/__init__.py`:

  ```python
  async def greet(name: str) -> str:
      return f"hello {name} from inside the sandbox"
  ```

  Then on the host:

  ```python
  from hello_agentix import greet
  result = await client.remote(greet, name="world")
  ```

- Declare a `default.nix` at this directory's root to add system
  binaries (git, ffmpeg, ...) the project needs but doesn't get from
  any plugin:

  ```nix
  { pkgs }: pkgs.symlinkJoin {
    name = "hello-agentix-sys";
    paths = with pkgs; [ git ffmpeg ];
  }
  ```
