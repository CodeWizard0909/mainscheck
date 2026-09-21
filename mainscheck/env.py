"""Minimal .env loading.

Hand-rolled rather than pulling in a dependency: the parsing is a dozen lines, and
code that touches a secret is worth being able to read in full.

The file is never printed, never logged, and never written to results. `.env` is in
.gitignore; if you move it, move that entry with it.
"""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: Path) -> list[str]:
    """Load KEY=VALUE pairs into os.environ. Returns the names it set.

    An existing environment variable always wins. That way an explicit
    `ANTHROPIC_API_KEY=... uv run ...` for a one-off run is not silently
    overridden by a stale value in the file.
    """
    if not path.exists():
        return []

    loaded: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue

        name, _, value = line.partition("=")
        name = name.strip()
        value = value.strip()

        # Strip one matching pair of surrounding quotes, if present.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]

        if not name or name in os.environ:
            continue

        os.environ[name] = value
        loaded.append(name)

    return loaded
