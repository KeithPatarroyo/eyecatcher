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
provides static display. For substrate="field" or "grid" the existing substrates
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
from ..signals.receptor import Receptor
from ..signals.sensory_system import SensorySystem
from .base import RepresentationBase
from .protocol import Phenotype, RepresentationOutput, Substrate


class {pascal}Genome:
    """Genome for {name} representation. Add fields and key (individual id)."""

    __slots__ = ("key",)

    def __init__(self, key: int = 0) -> None:
        self.key = key


class {pascal}Representation(RepresentationBase):
    """{pascal} representation. Set id, sensory_system, phenotype; see protocol."""

    id = "{name}"
    frontend_metadata = {{
        "hasSignalControls": True,
        "genomeKeys": ["key"],
    }}

    phenotype = Phenotype(substrate=Substrate(type="image"))

    def __init__(self, **kwargs: Any) -> None:
        # Presets: STANDARD_2D_INPUTS, TEMPORAL_INPUTS, MINIMAL_SPATIAL (catalog)
        self.display = Receptor(
            "display",
            inputs=(catalog.raw_time,),
            outputs=(),
            derived=(),
        )
        self.sensory_system = SensorySystem(receptors=(self.display,), outputs=())

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
        # TODO: produce actual output (e.g. grid, rule). See ca.py.
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
    # Add import after existing representation imports
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


def _update_init(
    name: str, pascal: str, content: str, *, has_genome: bool = True
) -> str:
    """Add import and __all__ entries for the new representation."""
    module = name
    if has_genome:
        import_line = f"from .{module} import {pascal}Genome, {pascal}Representation"
        all_extra = f'    "{pascal}Genome",\n    "{pascal}Representation",\n'
    else:
        import_line = f"from .{module} import {pascal}Representation"
        all_extra = f'    "{pascal}Representation",\n'
    if import_line in content:
        return content
    # Insert after last representation import
    last_import = None
    for m in re.finditer(r"^from \.\w+ import .+", content, re.MULTILINE):
        last_import = m
    if last_import is None:
        raise SystemExit("Could not find imports in representation/__init__.py")
    insert_after = last_import.end()
    content = content[:insert_after] + "\n" + import_line + content[insert_after:]

    # Add to __all__ (after last representation class)
    if f'"{pascal}Representation"' in content:
        return content
    # Match last representation entry before "export_representations_for_frontend"
    match = re.search(
        r'("[\w]+Representation",)\n(\s+"export_representations_for_frontend")',
        content,
    )
    if not match:
        raise SystemExit("Could not find __all__ representation list in __init__.py")
    old = match.group(0)
    new = f"{match.group(1)}\n    {all_extra.rstrip()},\n{match.group(2)}"
    content = content.replace(old, new, 1)
    return content


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _python_stub_field(name: str, pascal: str) -> str:
    """Stub for substrate=field (CPPN-like, one receptor, develop())."""
    return f'''"""
{pascal} representation: field substrate (CPPN-like). Scaffold: --substrate=field.

Implement: create_random, mutate, crossover, express, to_json, from_json.
Uses NeatReceptor + RuleAssembler; develop() returns GLSL rule.
See single_cppn.py and dual_cppn.py for full examples.
"""

from __future__ import annotations

from typing import Any

import neat

from .. import experiment
from ..signals import catalog
from ..signals.sensory_system import SensorySystem
from .field_base import (
    FieldRepresentationBase,
    _clamp_rgb,
    normalize_to_bipolar,
)
from .mixins import NetworkInspectable
from .protocol import Phenotype, Substrate
from .receptors import NeatReceptor


class {pascal}Representation(NetworkInspectable, FieldRepresentationBase):
    """Field substrate: one visual CPPN, rule from develop()."""

    id = "{name}"
    frontend_metadata = {{
        "hasSignalControls": True,
        "genomeKeys": ["visual"],
    }}
    phenotype = Phenotype(
        substrate=Substrate(type="field"),
        meta_template="Nodes: {{nodes}} | Connections: {{connections}}",
    )

    def __init__(self, neat_config_path: str | None = None, **kwargs: Any) -> None:
        self.visual = NeatReceptor(
            "visual",
            inputs=catalog.STANDARD_2D_INPUTS,
            outputs=catalog.RGB_OUTPUTS,
            derived=(catalog.DISTANCE,),
            config_path=neat_config_path or experiment.NEAT_CONFIG_PATH,
            role="primary",
        )
        self.sensory_system = SensorySystem(
            receptors=(self.visual,),
            outputs=catalog.RGB_OUTPUTS,
        )
        super().__init__(color_mode=kwargs.get("color_mode", "hsv"))

    @property
    def receptors(self) -> tuple[NeatReceptor, ...]:
        return (self.visual,)

    def _compile_contributions(self, genome: neat.DefaultGenome) -> dict[str, Any]:
        return {{"visual": self.visual.compile(genome)}}

    def query_rgb(
        self, genome: neat.DefaultGenome, inputs: dict[str, float]
    ) -> tuple[float, float, float]:
        out = self.visual.query(genome, inputs)
        return _clamp_rgb(out)

    def _sample_inputs(
        self, x: float, y: float, time: float, base: dict[str, float]
    ) -> dict[str, float]:
        return {{**base, "x": x, "y": y, catalog.time.id: time * 2.0 - 1.0}}

    def get_base_inputs_for_render(self) -> dict[str, float]:
        base = self.visual.default_values()
        base[catalog.time.id] = normalize_to_bipolar(0.0)
        return base
'''


def _python_stub_grid(name: str, pascal: str) -> str:
    """Stub for substrate=grid (FBO, update/display/interaction GLSL)."""
    return f'''"""
{pascal} representation: grid substrate. Scaffold: --substrate=grid.

Implement: create_random, mutate, crossover, express, to_json, from_json.
Phenotype supplies update_rule, display_rule, interaction_rule (GLSL).
See ca.py for a full example (Conway GOL).
"""

from __future__ import annotations

import random
from typing import Any

import numpy as np

from ..signals import catalog
from ..signals.receptor import Receptor
from ..signals.sensory_system import SensorySystem
from ._image_util import rgb_to_png_base64
from .base import RepresentationBase
from .mixins import GridAnalyzable, Saveable
from .protocol import Behaviour, Phenotype, RepresentationOutput, Substrate

DEFAULT_GRID_SIZE = 64

# Template GLSL: replace with your update logic (e.g. GOL, Lenia, reaction-diffusion).
_UPDATE_SHADER = """#version 300 es
precision highp float;
uniform sampler2D u_state;
uniform vec2 u_texelSize;
in vec2 vUV;
out vec4 fragColor;
void main() {{
    float c = texture(u_state, vUV).r;
    // TODO: sample neighbors, compute next state (e.g. GOL, Lenia kernel).
    fragColor = vec4(c, c, c, 1.0);
}}
"""

_DISPLAY_SHADER = """#version 300 es
precision highp float;
uniform sampler2D u_state;
in vec2 vUV;
out vec4 fragColor;
void main() {{
    float v = texture(u_state, vUV).r;
    fragColor = vec4(v, v, v, 1.0);
}}
"""


class {pascal}Genome:
    """Genome for {name}: initial grid + key. Customize for your representation."""

    __slots__ = ("grid", "key")

    def __init__(self, grid: np.ndarray, key: int = 0) -> None:
        self.grid = np.asarray(grid, dtype=np.uint8)
        self.key = key


class {pascal}Representation(GridAnalyzable, Saveable, RepresentationBase):
    """Grid substrate: FBO ping-pong, update/display/toggle from phenotype."""

    id = "{name}"
    frontend_metadata = {{
        "hasSignalControls": True,
        "genomeKeys": ["grid", "key"],
    }}
    phenotype = Phenotype(
        substrate=Substrate(
            type="grid",
            grid_size=DEFAULT_GRID_SIZE,
            state_format="RGBA",
            wrap="REPEAT",
        ),
        display_rule=_DISPLAY_SHADER,
        behaviour=Behaviour(
            update_rule=_UPDATE_SHADER,
            update_interval_ms=180,
            interaction_rule=None,
            interactions=(),
        ),
    )

    def __init__(self, **kwargs: Any) -> None:
        self.interaction = Receptor(
            "interaction",
            inputs=catalog.CA_INTERACTION_INPUTS,
            outputs=(),
        )
        self.sensory_system = SensorySystem(receptors=(self.interaction,), outputs=())

    def create_random(self, key: int = 0) -> {pascal}Genome:
        n = DEFAULT_GRID_SIZE
        grid = (np.random.random((n, n)) < 0.3).astype(np.uint8)
        return {pascal}Genome(grid=grid, key=key)

    def mutate(self, genome: {pascal}Genome, key: int) -> {pascal}Genome:
        grid = genome.grid.copy()
        r = random.randint(0, grid.shape[0] - 1)
        c = random.randint(0, grid.shape[1] - 1)
        grid[r, c] = 1 - grid[r, c]
        return {pascal}Genome(grid=grid, key=key)

    def crossover(
        self, a: {pascal}Genome, b: {pascal}Genome, key: int
    ) -> {pascal}Genome:
        mask = np.random.randint(0, 2, a.grid.shape)
        grid = np.where(mask, a.grid, b.grid)
        return {pascal}Genome(grid=grid, key=key)

    def express(
        self, genome: {pascal}Genome, inputs: dict[str, float], **kwargs: Any
    ) -> RepresentationOutput:
        # TODO: run your update rule for N steps, convert to RGB. See ca.py.
        rgb = np.zeros((DEFAULT_GRID_SIZE, DEFAULT_GRID_SIZE, 3), dtype=np.uint8)
        rgb[genome.grid > 0] = 255
        return RepresentationOutput("grid", rgb)

    def to_json(self, genome: {pascal}Genome) -> dict[str, Any]:
        return {{"key": genome.key, "grid": genome.grid.tolist()}}

    def from_json(self, data: dict[str, Any]) -> {pascal}Genome:
        key = int(data.get("key", 0))
        grid = np.asarray(data.get("grid", []), dtype=np.uint8)
        if grid.size == 0:
            grid = np.zeros((DEFAULT_GRID_SIZE, DEFAULT_GRID_SIZE), dtype=np.uint8)
        return {pascal}Genome(grid=grid, key=key)

    def serialize_output(
        self, output: RepresentationOutput, genome: Any = None
    ) -> dict[str, Any]:
        if output.output_type != "grid" or not hasattr(output.data, "shape"):
            return {{"image": "", "grid": []}}
        arr = np.asarray(output.data)
        b64 = rgb_to_png_base64(arr)
        return {{"image": "data:image/png;base64," + b64, "grid": arr.tolist()}}
'''


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold a new representation (Python, registry, includes)."
    )
    parser.add_argument(
        "name",
        help="Representation name in snake_case (e.g. my_rep, nca).",
    )
    parser.add_argument(
        "--substrate",
        choices=("image", "field", "grid"),
        default="image",
        help="Substrate type: image (static), field (CPPN/GLSL rule), grid (FBO).",
    )
    args = parser.parse_args()
    name = _validate_name(args.name.strip().lower())
    pascal = _snake_to_pascal(name)
    root = _repo_root()
    substrate = args.substrate

    def stub_for_substrate() -> str:
        if substrate == "field":
            return _python_stub_field(name, pascal)
        if substrate == "grid":
            return _python_stub_grid(name, pascal)
        return _python_stub(name, pascal)

    # 1. Write Python module
    py_path = root / "src" / "eyecatcher" / "representation" / f"{name}.py"
    if py_path.exists():
        print(f"Skip (exists): {py_path}", file=sys.stderr)
    else:
        py_path.parent.mkdir(parents=True, exist_ok=True)
        py_path.write_text(stub_for_substrate(), encoding="utf-8")
        print(f"Created: {py_path} (substrate={substrate})")

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
    has_genome = substrate != "field"
    new_init = _update_init(name, pascal, init_content, has_genome=has_genome)
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
        "or 'field'/'grid' for existing substrates."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
