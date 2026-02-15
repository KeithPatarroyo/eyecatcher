#!/usr/bin/env python3
"""
Update representation script includes in HTML templates from a single ordered list.

Adding a new representation script = add one entry to REPRESENTATION_SCRIPTS and run:
  python scripts/generate_representation_includes.py
  or: make generate-representation-includes

Run from repo root. Rewrites static/interactive_viewer.html and
static/genealogy_viewer.html so the contiguous block of js/representation/*.js
script tags is exactly this list. Load order: webgl_utils before substrates;
registry after config.
"""

import os
import re

# Single source of truth: representation script basenames in load order.
# WebGLUtils before shader/grid substrates; substrate_registry and registry last.
# Unified config (js/config.generated.js) is loaded earlier in the page, not here.
REPRESENTATION_SCRIPTS = [
    "substrate.js",
    "image_substrate.js",
    "webgl_utils.js",
    "shader_substrate.js",
    "grid_substrate.js",
    "substrate_registry.js",
    "registry.js",
]

SCRIPT_PREFIX = "js/representation/"
INDENT = "        "  # 8 spaces to match existing HTML


def _repo_root() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)


def _generate_block() -> str:
    lines = [
        f'{INDENT}<script src="{SCRIPT_PREFIX}{name}"></script>'
        for name in REPRESENTATION_SCRIPTS
    ]
    return "\n".join(lines)


def _replace_representation_block(content: str) -> str:
    """Replace js/substrate/ or js/representation/ script block with canonical block."""
    pattern = re.compile(
        r"^(\s*)<script src=\"js/(?:substrate|representation)/[^\"]+\"></script>\n",
        re.MULTILINE,
    )
    first = None
    last = None
    for m in pattern.finditer(content):
        if first is None:
            first = m.start()
        last = m.end()

    if first is None or last is None:
        return content
    block = _generate_block()
    return content[:first] + block + "\n" + content[last:]


def main() -> None:
    root = _repo_root()
    static_dir = os.path.join(root, "static")
    html_files = [
        os.path.join(static_dir, "interactive_viewer.html"),
        os.path.join(static_dir, "genealogy_viewer.html"),
    ]
    for path in html_files:
        with open(path, encoding="utf-8") as f:
            content = f.read()
        new_content = _replace_representation_block(content)
        if new_content != content:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Updated {path}")
        else:
            os.utime(path, None)  # touch so codegen sync sees output as up to date
            print(f"Unchanged {path}")


if __name__ == "__main__":
    main()
