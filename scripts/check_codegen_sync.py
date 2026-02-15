#!/usr/bin/env python3
"""
Check that generated files are not stale relative to their sources.

Exits 0 if all codegen outputs are up to date, 1 otherwise with message:
"Generated files are stale. Run: make generate."

Run from repo root: python scripts/check_codegen_sync.py
Or: make check-generate

Suitable for CI or before dev server startup.
"""

import os
import sys


def _repo_root() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)


def _file_mtime(path: str) -> float:
    if os.path.isfile(path):
        return os.path.getmtime(path)
    return 0.0


def _dir_max_mtime(path: str, ext: str = ".py") -> float:
    if not os.path.isdir(path):
        return 0.0
    best = 0.0
    for root, _dirs, files in os.walk(path):
        for f in files:
            if f.endswith(ext):
                best = max(best, os.path.getmtime(os.path.join(root, f)))
    return best


def _check_stale(
    root: str,
    output: str,
    sources: list[str],
    dir_sources: list[str] | None = None,
) -> bool:
    """Return True if output is missing or older than any source."""
    out_path = os.path.join(root, output) if not os.path.isabs(output) else output
    out_mtime = _file_mtime(out_path)
    if out_mtime == 0:
        return True  # missing
    for s in sources:
        p = os.path.join(root, s) if not s.startswith("/") else s
        if os.path.isfile(p) and os.path.getmtime(p) > out_mtime:
            return True
    for d in dir_sources or []:
        full = os.path.join(root, d)
        if _dir_max_mtime(full) > out_mtime:
            return True
    return False


def main() -> int:
    root = _repo_root()
    stale = False

    # Unified config: static/js/config.generated.js (representations, signals, defaults)
    if _check_stale(
        root,
        "static/js/config.generated.js",
        [
            "scripts/generate_config.py",
            "config/evolution_defaults.json",
        ],
        dir_sources=[
            "src/eyecatcher/representation",
            "src/eyecatcher/signals",
        ],
    ):
        stale = True

    # Representation includes: HTML script blocks
    if _check_stale(
        root,
        "static/interactive_viewer.html",
        ["scripts/generate_representation_includes.py"],
    ) or _check_stale(
        root,
        "static/genealogy_viewer.html",
        ["scripts/generate_representation_includes.py"],
    ):
        stale = True

    if stale:
        print(
            "Generated files are stale. Run: make generate.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
