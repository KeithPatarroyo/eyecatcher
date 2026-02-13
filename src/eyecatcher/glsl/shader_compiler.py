"""
Compiles neural networks to GLSL fragment shaders.

Orchestrates compiler_topology, node_code_generator, and activation_registry.
Researchers extend: activation in activation_registry + node_code_generator;
output (HSV/RGB) in _get_color_output_code; signals passed at construction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import neat

from ..signals import build_glsl_input_map
from .activation_registry import get_glsl_block
from .compiler_topology import get_enabled_connections, topological_sort

if TYPE_CHECKING:
    from ..representation import DualGenome
from .node_code_generator import generate_node_code, generate_time_signal_code


def _default_signals():
    """Lazy import to avoid circular imports; used when constructor gets None."""
    from ..signals import (
        TIME_INPUTS,
        VISUAL_DERIVED_INPUTS,
        VISUAL_INPUTS,
    )

    return VISUAL_INPUTS, TIME_INPUTS, VISUAL_DERIVED_INPUTS


class ShaderCompiler:
    """
    Compiles neural networks into GLSL fragment shader code.
    The shader can then be executed on GPU for real-time rendering.

    Args:
        visual_signals: Input signals for the visual network (default from registry).
        time_signals: Input signals for the time network, or None for single-CPPN.
        derived_signals: Derived spatial inputs for visual (default from registry).
        color_mode: 'hsv' (Picbreeder-style) or 'rgb' (direct RGB output)
    """

    def __init__(
        self,
        visual_signals=None,
        time_signals=None,
        derived_signals=None,
        color_mode: str = "hsv",
    ):
        if visual_signals is None or time_signals is None or derived_signals is None:
            v, t, d = _default_signals()
            visual_signals = visual_signals if visual_signals is not None else v
            time_signals = time_signals if time_signals is not None else t
            derived_signals = derived_signals if derived_signals is not None else d
        self.visual_signals = list(visual_signals)
        self.time_signals = list(time_signals) if time_signals else []
        self.derived_signals = list(derived_signals)
        self.node_order = []
        self.node_code = {}
        self.color_mode = color_mode

    def with_color_mode(self, color_mode: str) -> ShaderCompiler:
        """Return a new compiler with the same signals but different color_mode."""
        return ShaderCompiler(
            self.visual_signals,
            self.time_signals,
            self.derived_signals,
            color_mode=color_mode,
        )

    def compile(
        self,
        genome_or_dual: neat.DefaultGenome | DualGenome,
        visual_config: neat.Config,
        time_config: neat.Config | None = None,
    ) -> str:
        """
        Compile a genome (or dual genome) into GLSL shader code.

        Single-CPPN: pass a neat.DefaultGenome and time_config=None.
        Dual-CPPN: pass a DualGenome and time_config for the time signal network.

        Args:
            genome_or_dual: NEAT genome (single) or DualGenome (dual)
            visual_config: NEAT configuration for the visual network
            time_config: NEAT config for time network, or None for single-CPPN

        Returns:
            Complete GLSL fragment shader code as string
        """
        # Lazy import to avoid circular import: representation -> dual_cppn -> glsl
        from ..representation import DualGenome

        if time_config is not None and isinstance(genome_or_dual, DualGenome):
            time_code = generate_time_signal_code(
                genome_or_dual.time_signal,
                time_config,
                time_inputs=self.time_signals,
            )
            visual_genome = genome_or_dual.visual
        else:
            time_code = None
            visual_genome = genome_or_dual  # type: ignore[assignment]

        connections = get_enabled_connections(visual_genome)
        nodes = topological_sort(visual_genome, connections, visual_config)
        visual_code = generate_node_code(
            visual_genome,
            connections,
            nodes,
            visual_config,
            input_names=build_glsl_input_map(self.visual_signals),
        )
        return self._build_main_body(visual_code, visual_config, time_code=time_code)

    def _get_color_output_code(self, num_outputs: int = 3) -> str:
        """Get GLSL code for converting network outputs to RGB based on color_mode."""
        if self.color_mode == "rgb":
            r = "clamp((output_0 + 1.0) * 0.5, 0.0, 1.0)" if num_outputs >= 1 else "0.0"
            g = "clamp((output_1 + 1.0) * 0.5, 0.0, 1.0)" if num_outputs >= 2 else "0.0"
            b = "clamp((output_2 + 1.0) * 0.5, 0.0, 1.0)" if num_outputs >= 3 else "0.0"
            return f"""    // Output RGB directly (clamp to 0-1)
    float r = {r};
    float g = {g};
    float b = {b};

    fragColor = vec4(r, g, b, 1.0);"""
        else:  # hsv
            return """    // Interpret outputs as HSV - Picbreeder style
    // Hue: sigmoid (0.4x); ~0 cyan, ~±5 orange/magenta, ~±10 red
    float h = 1.0 / (1.0 + exp(-output_0 * 0.4));
    float s = clamp((output_1 + 1.0) * 0.5, 0.0, 1.0);  // Saturation 0-1
    float v = clamp(abs(output_2), 0.0, 1.0);  // Value (Picbreeder)

    // Branchless HSV to RGB (lolengine.net)
    vec4 K = vec4(1.0, 2.0/3.0, 1.0/3.0, 3.0);
    vec3 p = abs(fract(vec3(h,h,h) + K.xyz) * 6.0 - K.www);
    vec3 rgb = v * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), s);

    fragColor = vec4(rgb, 1.0);"""

    def _glsl_uniform_declarations(self) -> str:
        """Generate uniform float declarations for shared signal uniforms (u_{id})."""
        seen = set()
        lines = []
        for sig_list in (self.time_signals, self.visual_signals):
            for s in sig_list:
                u = s._uniform()
                if u and u not in seen:
                    seen.add(u)
                    lines.append(f"uniform float {u};")
        return "\n".join(lines)

    def _glsl_enable_declarations(self) -> str:
        """Generate enable toggle uniforms (uTimeEnable_{id}, uVisualEnable_{id})."""
        lines = []
        for prefix, sig_list in (
            ("Time", self.time_signals),
            ("Visual", self.visual_signals),
        ):
            for s in sig_list:
                if not s.is_spatial and s.id != "bias":
                    lines.append(f"uniform float u{prefix}Enable_{s.id};")
        return "\n".join(lines)

    def _glsl_enable_gating(
        self, signals: list, prefix: str, base_vars: bool = True
    ) -> str:
        """Generate gated input assignments for a signal list (time or visual)."""
        lines = []
        for s in signals:
            if not s.is_spatial and s.id != "bias":
                val = f"{s.id}_base" if base_vars else f"({s._uniform()} * 2.0 - 1.0)"
                lines.append(
                    f"    float {s._glsl_var()} = {val} * u{prefix}Enable_{s.id};"
                )
            elif s.id == "bias":
                lines.append("    float v_bias = 1.0;")
        return "\n".join(lines)

    def _glsl_base_scaling(self) -> str:
        """Generate base scaled vars (raw_time_base = u_raw_time*2-1 etc) for time."""
        lines = []
        for s in self.time_signals:
            u = s._uniform()
            if u:
                lines.append(f"    float {s.id}_base = {u} * 2.0 - 1.0;")
        return "\n".join(lines)

    def _glsl_time_enable_gating(self) -> str:
        """Generate time network gated input assignments."""
        return self._glsl_enable_gating(self.time_signals, "Time", base_vars=True)

    def _glsl_header(self) -> str:
        """Shared GLSL header: version, precision, in/out, uniforms, enable decls."""
        uniform_decls = self._glsl_uniform_declarations()
        enable_decls = self._glsl_enable_declarations()
        return f"""#version 300 es
precision highp float;

// Inputs from vertex shader
in vec2 vUV;  // UV coordinates (0-1)
{uniform_decls}

// Signal enable toggles (0.0 = disabled/neutral, 1.0 = enabled)
{enable_decls}

// Output color
out vec4 fragColor;
{get_glsl_block()}"""

    def _glsl_uv_to_coord(self) -> str:
        """UV to coord space (-1..1) and derived spatial inputs from registry."""
        lines = [
            "    float v_x = vUV.x * 2.0 - 1.0;",
            "    float v_y = vUV.y * 2.0 - 1.0;",
        ]
        for d in self.derived_signals:
            lines.append(f"    {d.glsl}")
        return "\n".join(lines)

    def _build_shader(self, main_body: str, num_outputs: int = 3) -> str:
        """Build complete GLSL shader from header, main body, and color output."""
        return f"""{self._glsl_header()}

void main() {{
{main_body}

{self._get_color_output_code(num_outputs)}
}}
"""

    def _glsl_visual_enable_gating(self, use_time_from_network: bool) -> str:
        """Generate visual network gated input assignments.

        When use_time_from_network is True (dual-CPPN build), time uses
        timeFromNetwork and others use _base (reassign without 'float' where
        already declared in time section). Otherwise all use inline (uniform*2-1)
        for single-CPPN mode.
        """
        lines = []
        time_ids = {t.id for t in self.time_signals}
        for s in self.visual_signals:
            if s.is_spatial or s.id == "bias":
                if s.id == "bias":
                    if use_time_from_network:
                        lines.append("    v_bias = 1.0;")
                    else:
                        lines.append("    float v_bias = 1.0;")
                continue
            if use_time_from_network:
                if s.id == "time":
                    lines.append(
                        f"    float {s._glsl_var()} = "
                        f"timeFromNetwork * uVisualEnable_{s.id};"
                    )
                else:
                    u = s._uniform()
                    already_declared = s.id in time_ids
                    expr = f"({u} * 2.0 - 1.0) * uVisualEnable_{s.id}"
                    if already_declared:
                        lines.append(f"    {s._glsl_var()} = {expr};")
                    else:
                        lines.append(f"    float {s._glsl_var()} = {expr};")
            else:
                u = s._uniform()
                lines.append(
                    f"    float {s._glsl_var()} = "
                    f"({u} * 2.0 - 1.0) * uVisualEnable_{s.id};"
                )
        return "\n".join(lines)

    def _build_main_body(
        self,
        visual_code: str,
        visual_config: neat.Config,
        time_code: str | None = None,
    ) -> str:
        """Build the complete GLSL shader main body and final shader.

        If time_code is provided (dual-CPPN), includes time network section first,
        then visual. Otherwise (single-CPPN) only visual network.
        """
        num_outputs = visual_config.genome_config.num_outputs
        if time_code is not None:
            base_scaling = self._glsl_base_scaling()
            time_gating = self._glsl_time_enable_gating()
            visual_gating = self._glsl_visual_enable_gating(use_time_from_network=True)
            main_body = f"""    // Raw inputs (before enable gating)
{base_scaling}

    // === TIME SIGNAL NETWORK ===
    // Apply enable gates for time network inputs (disabled = 0.0 neutral)
{time_gating}

    // Time signal network computation
{time_code}

    // Get modified time from time signal network (clamped to valid range)
    float timeFromNetwork = clamp(time_output_0, -1.0, 1.0);

    // === VISUAL NETWORK ===
    // Convert UV to coordinate space (-1 to 1)
{self._glsl_uv_to_coord()}

    // Apply enable gates for visual network inputs (disabled = 0.0 neutral)
{visual_gating}

    // Visual network computations (using modified time)
{visual_code}"""
        else:
            visual_gating = self._glsl_visual_enable_gating(use_time_from_network=False)
            main_body = f"""    // Convert UV to coordinate space (-1 to 1)
{self._glsl_uv_to_coord()}

    // Apply enable gates (disabled = 0.0 neutral)
{visual_gating}

    // Network computations
{visual_code}"""
        return self._build_shader(main_body, num_outputs)
