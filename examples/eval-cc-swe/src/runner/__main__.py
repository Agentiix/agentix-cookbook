"""`python -m runner --limit N` entry point."""

from __future__ import annotations

import asyncio
import sys

from runner import main

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
