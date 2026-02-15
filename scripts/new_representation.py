#!/usr/bin/env python3
"""
Scaffold a new representation: Python module, registry entry, and exports.

Usage:
  make new-representation name=<name>
  python scripts/new_representation.py <name>

Example:
  make new-representation name=my_rep
  python scripts/new_representation.py my_rep

Creates:
  - src/eyecatcher/representation/<name>.py (stub with Phenotype)
  - Updates src/eyecatcher/representation/registry.py
  - Updates src/eyecatcher/representation/__init__.py (export)

No JavaScript is generated. The frontend uses Phenotype (substrate) from config;
run make generate to export. For substrate="image" the backend render_to_image()
provides static display. For substrate="shader" or "grid" the existing substrates
render from your phenotype. Prints a preset snippet for config/experiments.json.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _repo_root() -> Path:
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent


def _snake_to_pascal(snake: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in snake.split("_"))


def _validate_name(name: str) -> str:
    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        raise SystemExit(
            "Name must be snake_case (lowercase, digits/underscores; "
            f"start with letter). Got: {name!r}"
        )
    return name


# ---------------------------------------------------------------------------
# Python stub
# ---------------------------------------------------------------------------


def _python_stub(name: str, pascal: str) -> str:
    return f'''"""
{pascal} representation: scaffold from scripts/new_representation.py.

Implement: create_random, mutate, crossover, express, to_json, from_json.
Optional: develop, serialize_output, etc. See base.py and protocol.py.
"""

from __future__ import annotations

import random
from typing import Any

from ..signals import catalog
from ..signals.socket import Socket
from ..signals.spec import SignalSpec
from .base import RepresentationBase
from .protocol import OutputType, Phenotype, RepresentationOutput


class {pascal}Genome:
    """Genome for {name} representation. Add fields and key (individual id)."""

    __slots__ = ("key",)

    def __init__(self, key: int = 0) -> None:
        self.key = key


class {pascal}Representation(RepresentationBase):
    """{pascal} representation. Set id, signal_spec; implement protocol methods."""

    id = "{name}"
    output_type: OutputType = "grid"
    frontend_metadata = {{
        "hasSignalControls": True,
        "genomeKeys": ["key"],
    }}

    phenotype = Phenotype(substrate="image")

    def __init__(self, **kwargs: Any) -> None:
        self.display = Socket(
            "display",
            inputs=(catalog.raw_time,),
            outputs=(),
            derived=(),
        )
        self.signal_spec = SignalSpec(sockets=(self.display,), outputs=())

    def create_random(self, key: int = 0) -> {pascal}Genome:
        return {pascal}Genome(key=key)

    def mutate(self, ind: {pascal}Genome, key: int) -> {pascal}Genome:
        return {pascal}Genome(key=key)

    def crossover(
        self, a: {pascal}Genome, b: {pascal}Genome, key: int
    ) -> {pascal}Genome:
        return {pascal}Genome(key=key)

    def express(
        self, ind: {pascal}Genome, inputs: dict[str, float], **kwargs: Any
    ) -> RepresentationOutput:
        # TODO: produce actual output (e.g. grid, shader). See trivial.py / ca.py.
        import numpy as np
        rgb = np.zeros((16, 16, 3), dtype=np.uint8)
        return RepresentationOutput("grid", rgb)

    def to_json(self, ind: {pascal}Genome) -> dict[str, Any]:
        return {{"key": ind.key}}

    def from_json(self, data: dict[str, Any]) -> {pascal}Genome:
        key = int(data.get("key", 0))
        return {pascal}Genome(key=key)
'''


# ---------------------------------------------------------------------------
# Registry update
# ---------------------------------------------------------------------------


def _update_registry(name: str, pascal: str, content: str) -> str:
    """Add import and REPRESENTATIONS entry for the new representation."""
    module = name
    class_name = f"{pascal}Representation"
    # Add import after existing from .trivial import ...
    import_line = f"from .{module} import {class_name}"
    if import_line in content:
        return content

    # Find last representation import
    last_import = None
    for m in re.finditer(
        r"^from \.\w+ import \w+Representation", content, re.MULTILINE
    ):
        last_import = m

    if last_import is None:
        raise SystemExit("Could not find representation import in registry.py")
    insert_after = last_import.end()
    content = content[:insert_after] + "\n" + import_line + content[insert_after:]

    # Add to REPRESENTATIONS dict: "name": ClassName,
    entry = f'    "{name}": {class_name},'
    if f'"{name}"' in content and class_name in content:
        return content
    # Insert after the last dict entry (line ending with ",)
    match = re.search(
        r'^(\s+"[^"]+": \w+Representation,)\n(\s*\})',
        content,
        re.MULTILINE,
    )
    if not match:
        raise SystemExit("Could not find REPRESENTATIONS dict in registry.py")
    content = content[: match.end(1)] + "\n" + entry + "\n" + content[match.start(2) :]
    return content


# ---------------------------------------------------------------------------
# __init__.py export update
# ---------------------------------------------------------------------------


def _update_init(name: str, pascal: str, content: str) -> str:
    """Add import and __all__ entries for the new representation."""
    module = name
    import_line = f"from .{module} import {pascal}Genome, {pascal}Representation"
    if import_line in content:
        return content
    # Insert after last representation import (e.g. from .trivial import ...)
    last_import = None
    for m in re.finditer(r"^from \.\w+ import .+", content, re.MULTILINE):
        last_import = m
    if last_import is None:
        raise SystemExit("Could not find imports in representation/__init__.py")
    insert_after = last_import.end()
    content = content[:insert_after] + "\n" + import_line + content[insert_after:]

    # Add to __all__ (after TrivialRepresentation)
    if f'"{pascal}Representation"' in content:
        return content
    old = '"TrivialRepresentation",\n    "export_representations_for_frontend"'
    new = (
        f'"TrivialRepresentation",\n    "{pascal}Genome",\n'
        f'    "{pascal}Representation",\n    "export_representations_for_frontend"'
    )
    content = content.replace(old, new, 1)
    return content


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold a new representation (Python, registry, includes)."
    )
    parser.add_argument(
        "name",
        help="Representation name in snake_case (e.g. my_rep, nca).",
    )
    args = parser.parse_args()
    name = _validate_name(args.name.strip().lower())
    pascal = _snake_to_pascal(name)
    root = _repo_root()

    # 1. Write Python module
    py_path = root / "src" / "eyecatcher" / "representation" / f"{name}.py"
    if py_path.exists():
        print(f"Skip (exists): {py_path}", file=sys.stderr)
    else:
        py_path.parent.mkdir(parents=True, exist_ok=True)
        py_path.write_text(_python_stub(name, pascal), encoding="utf-8")
        print(f"Created: {py_path}")

    # 2. Update registry
    registry_path = root / "src" / "eyecatcher" / "representation" / "registry.py"
    reg_content = registry_path.read_text(encoding="utf-8")
    new_reg = _update_registry(name, pascal, reg_content)
    if new_reg != reg_content:
        registry_path.write_text(new_reg, encoding="utf-8")
        print(f"Updated: {registry_path}")
    else:
        print(f"Unchanged (already registered): {registry_path}")

    # 3. Update __init__.py exports
    init_path = root / "src" / "eyecatcher" / "representation" / "__init__.py"
    init_content = init_path.read_text(encoding="utf-8")
    new_init = _update_init(name, pascal, init_content)
    if new_init != init_content:
        init_path.write_text(new_init, encoding="utf-8")
        print(f"Updated: {init_path}")
    else:
        print(f"Unchanged (already exported): {init_path}")

    # 4. Preset snippet
    print()
    print("Add this preset to config/experiments.json (optional):")
    print()
    snippet = (
        f'  "{name}": {{"representation": "{name}", "population_size": 8, '
        f'"max_population_size": 24, "crossover_probability": 0.3}}'
    )
    print(snippet)
    print()
    print("Then run: make generate")
    print()
    print(
        "No JavaScript is generated. Representation uses phenotype.substrate "
        "from config."
    )
    print(
        "Use substrate='image' for static display (render_to_image()), "
        "or 'shader'/'grid' for existing substrates."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
