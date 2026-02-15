"""
Assembles receptor contributions into a complete rendering rule.

Takes NetworkContribution(s) from NeatReceptor.compile() and produces
the full rule string. No genome or NEAT types in the public API.
"""

from __future__ import annotations

from ..representation.receptors import NetworkContribution
from ..signals.sensory_system import SensorySystem, Signal
from .activation_registry import get_glsl_block
from .codegen import generate_node_code
from .input_map import glsl_uniform_name, glsl_var_name


class RuleAssembler:
    """
    Assembles receptor contributions into a complete rendering rule.

    Built from a SensorySystem; assemble(visual, time?) produces the rule string.
    """

    def __init__(
        self,
        visual_signals: list[Signal],
        time_signals: list[Signal] | None,
        derived_signals: list,
        color_mode: str = "hsv",
        substitutions: dict[str, str] | None = None,
    ):
        self.visual_signals = list(visual_signals)
        self.time_signals = list(time_signals) if time_signals else []
        self.derived_signals = list(derived_signals)
        self.substitutions = dict(substitutions) if substitutions else {}
        self.color_mode = color_mode

    @classmethod
    def from_sensory_system(
        cls, sensory_system: SensorySystem, *, color_mode: str = "hsv"
    ) -> RuleAssembler:
        """Build a RuleAssembler from a SensorySystem."""
        try:
            visual_rec = sensory_system.receptor("visual")
        except KeyError:
            visual_rec = (
                sensory_system.receptors[0] if sensory_system.receptors else None
            )
        try:
            time_rec = sensory_system.receptor("time")
        except KeyError:
            time_rec = None
        return cls(
            visual_signals=list(visual_rec.inputs) if visual_rec else [],
            time_signals=list(time_rec.inputs) if time_rec else None,
            derived_signals=list(visual_rec.derived) if visual_rec else [],
            color_mode=color_mode,
            substitutions=sensory_system.substitutions or None,
        )

    def with_color_mode(self, color_mode: str) -> RuleAssembler:
        """Return a new assembler with the same signals but different color_mode."""
        return RuleAssembler(
            self.visual_signals,
            self.time_signals,
            self.derived_signals,
            color_mode=color_mode,
            substitutions=self.substitutions,
        )

    def _toggleable_signals(self) -> list[Signal]:
        seen: set[str] = set()
        out: list[Signal] = []
        for sig_list in (self.time_signals, self.visual_signals):
            for s in sig_list:
                if not s.is_spatial and not s.is_constant and s.id not in seen:
                    seen.add(s.id)
                    out.append(s)
        return out

    def _get_color_output_code(self, num_outputs: int = 3) -> str:
        if self.color_mode == "rgb":
            r = "clamp((output_0 + 1.0) * 0.5, 0.0, 1.0)" if num_outputs >= 1 else "0.0"
            g = "clamp((output_1 + 1.0) * 0.5, 0.0, 1.0)" if num_outputs >= 2 else "0.0"
            b = "clamp((output_2 + 1.0) * 0.5, 0.0, 1.0)" if num_outputs >= 3 else "0.0"
            return f"""    // Output RGB directly (clamp to 0-1)
    float r = {r};
    float g = {g};
    float b = {b};

    fragColor = vec4(r, g, b, 1.0);"""
        else:
            return """    // Interpret outputs as HSV - Picbreeder style
    float h = 1.0 / (1.0 + exp(-output_0 * 0.4));
    float s = clamp((output_1 + 1.0) * 0.5, 0.0, 1.0);
    float v = clamp(abs(output_2), 0.0, 1.0);
    vec4 K = vec4(1.0, 2.0/3.0, 1.0/3.0, 3.0);
    vec3 p = abs(fract(vec3(h,h,h) + K.xyz) * 6.0 - K.www);
    vec3 rgb = v * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), s);
    fragColor = vec4(rgb, 1.0);"""

    def _glsl_uniform_declarations(self) -> str:
        seen = set()
        lines = []
        for sig_list in (self.time_signals, self.visual_signals):
            for s in sig_list:
                u = glsl_uniform_name(s)
                if u and u not in seen:
                    seen.add(u)
                    lines.append(f"uniform float {u};")
        return "\n".join(lines)

    def _glsl_enable_declarations(self) -> str:
        lines = []
        for s in self._toggleable_signals():
            lines.append(f"uniform float uEnable_{s.id};")
        return "\n".join(lines)

    def _glsl_enable_gating(self, signals: list[Signal], base_vars: bool = True) -> str:
        lines = []
        for s in signals:
            if s.is_constant:
                lines.append(f"    float {glsl_var_name(s)} = {s.default};")
            elif not s.is_spatial:
                u = glsl_uniform_name(s)
                val = f"{s.id}_base" if base_vars else f"({u} * 2.0 - 1.0)"
                lines.append(f"    float {glsl_var_name(s)} = {val} * uEnable_{s.id};")
        return "\n".join(lines)

    def _glsl_base_scaling(self) -> str:
        lines = []
        for s in self.time_signals:
            u = glsl_uniform_name(s)
            if u:
                lines.append(f"    float {s.id}_base = {u} * 2.0 - 1.0;")
        return "\n".join(lines)

    def _glsl_uv_to_coord(self) -> str:
        lines = [
            "    float v_x = vUV.x * 2.0 - 1.0;",
            "    float v_y = vUV.y * 2.0 - 1.0;",
        ]
        for d in self.derived_signals:
            lines.append(f"    {d.render_code}")
        return "\n".join(lines)

    def _glsl_visual_enable_gating(self, use_time_from_network: bool) -> str:
        lines = []
        time_ids = {t.id for t in self.time_signals}
        for s in self.visual_signals:
            if s.is_spatial:
                continue
            if s.is_constant:
                v = glsl_var_name(s)
                if use_time_from_network and s.id in time_ids:
                    lines.append(f"    {v} = {s.default};")
                else:
                    lines.append(f"    float {v} = {s.default};")
                continue
            if use_time_from_network and s.id in self.substitutions:
                expr = f"{self.substitutions[s.id]} * uEnable_{s.id}"
                lines.append(f"    float {glsl_var_name(s)} = {expr};")
                continue
            u = glsl_uniform_name(s)
            expr = f"({u} * 2.0 - 1.0) * uEnable_{s.id}"
            if use_time_from_network and s.id in time_ids:
                lines.append(f"    {glsl_var_name(s)} = {expr};")
            else:
                lines.append(f"    float {glsl_var_name(s)} = {expr};")
        return "\n".join(lines)

    def _glsl_header(self) -> str:
        uniform_decls = self._glsl_uniform_declarations()
        enable_decls = self._glsl_enable_declarations()
        return f"""#version 300 es
precision highp float;
in vec2 vUV;
{uniform_decls}
{enable_decls}
out vec4 fragColor;
{get_glsl_block()}"""

    def _build_rule(self, main_body: str, num_outputs: int = 3) -> str:
        return f"""{self._glsl_header()}

void main() {{
{main_body}

{self._get_color_output_code(num_outputs)}
}}
"""

    def assemble(
        self,
        visual: NetworkContribution,
        time: NetworkContribution | None = None,
    ) -> str:
        """Produce the full rendering rule from visual and optional time
        contribution.
        """
        visual_code = generate_node_code(visual)
        time_code = generate_node_code(time) if time else None
        num_outputs = visual.num_outputs

        if time_code is not None:
            base_scaling = self._glsl_base_scaling()
            time_gating = self._glsl_enable_gating(self.time_signals, base_vars=True)
            visual_gating = self._glsl_visual_enable_gating(use_time_from_network=True)
            main_body = f"""    // Raw inputs (before enable gating)
{base_scaling}

    // === TIME SIGNAL NETWORK ===
{time_gating}

{time_code}

    float timeFromNetwork = clamp(time_output_0, -1.0, 1.0);

    // === VISUAL NETWORK ===
{self._glsl_uv_to_coord()}

{visual_gating}

{visual_code}"""
        else:
            visual_gating = self._glsl_visual_enable_gating(use_time_from_network=False)
            main_body = f"""    // Convert UV to coordinate space (-1 to 1)
{self._glsl_uv_to_coord()}

{visual_gating}

{visual_code}"""
        return self._build_rule(main_body, num_outputs)
