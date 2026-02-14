#!/usr/bin/env python3
"""
Update substrate script includes in HTML templates from a single ordered list.

Adding a new adapter = add one entry to SUBSTRATE_SCRIPTS below and run:
  python scripts/generate_substrate_includes.py
  or: make generate-substrate-includes

Run from repo root. Rewrites static/interactive_viewer.html and
static/genealogy_viewer.html so the contiguous block of js/substrate/*.js
script tags is exactly this list. Load order matters: registry and
stateful_adapter before adapters that use them; pattern_renderer last.
"""

import os
import re

# Single source of truth: substrate script basenames in load order.
# Add new adapters here (e.g. "nca.js"); do not edit the HTML files by hand.
SUBSTRATE_SCRIPTS = [
    "cppn_adapter.js",
    "config.generated.js",
    "registry.js",
    "stateful_adapter.js",
    "ca.js",
    "pattern_renderer.js",
]

SCRIPT_PREFIX = "js/substrate/"
INDENT = "        "  # 8 spaces to match existing HTML


def _repo_root() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)


def _generate_block() -> str:
    lines = [
        f'{INDENT}<script src="{SCRIPT_PREFIX}{name}"></script>'
        for name in SUBSTRATE_SCRIPTS
    ]
    return "\n".join(lines)


def _replace_substrate_block(content: str) -> str:
    """Replace contiguous js/substrate/ script tag block with canonical block."""
    pattern = re.compile(
        r"^(\s*)<script src=\"js/substrate/[^\"]+\"></script>\n",
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
        new_content = _replace_substrate_block(content)
        if new_content != content:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Updated {path}")
        else:
            print(f"Unchanged {path}")


if __name__ == "__main__":
    main()
