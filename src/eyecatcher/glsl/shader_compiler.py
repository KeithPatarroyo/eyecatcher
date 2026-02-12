"""
Compiles CPPN networks (single or dual visual + time) to GLSL fragment shaders.

Orchestrates compiler_topology, node_code_generator, and glsl_fragments.
Researchers extend: activation in glsl_fragments + node_code_generator;
output (HSV/RGB) in _get_color_output_code; signals in signals.py.
"""

import neat

from ..genome import DualGenome
from ..signals import TIME_INPUTS, VISUAL_INPUTS
from .compiler_topology import get_enabled_connections, topological_sort
from .glsl_fragments import ACTIVATION_GLSL_BLOCK
from .node_code_generator import generate_node_code, generate_time_signal_code


class ShaderCompiler:
    """
    Compiles CPPN networks into GLSL fragment shader code.
    The shader can then be executed on GPU for real-time rendering.

    Args:
        color_mode: 'hsv' (Picbreeder-style) or 'rgb' (direct RGB output)
    """

    def __init__(self, color_mode: str = "hsv"):
        self.node_order: list = []
        self.node_code: dict = {}
        self.color_mode = color_mode  # 'hsv' or 'rgb'

    def compile_to_glsl(
        self, genome: neat.DefaultGenome, visual_config: neat.Config
    ) -> str:
        """
        Compile a CPPN genome into GLSL shader code.

        Args:
            genome: NEAT genome to compile
            visual_config: NEAT configuration for the genome

        Returns:
            Complete GLSL fragment shader code as string
        """
        connections = get_enabled_connections(genome)
        nodes = topological_sort(genome, connections, visual_config)
        node_computations = generate_node_code(
            genome, connections, nodes, visual_config
        )
        return self._build_shader_template(node_computations, visual_config)

    def _get_color_output_code(self) -> str:
        """Get GLSL code for converting CPPN outputs to RGB based on color_mode."""
        if self.color_mode == "rgb":
            return """    // Output RGB directly (clamp to 0-1)
    float r = clamp((output_0 + 1.0) * 0.5, 0.0, 1.0);
    float g = clamp((output_1 + 1.0) * 0.5, 0.0, 1.0);
    float b = clamp((output_2 + 1.0) * 0.5, 0.0, 1.0);

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
        for sig_list in (TIME_INPUTS, VISUAL_INPUTS):
            for s in sig_list:
                u = s._uniform()
                if u and u not in seen:
                    seen.add(u)
                    lines.append(f"uniform float {u};")
        return "\n".join(lines)

    def _glsl_enable_declarations(self) -> str:
        """Generate enable toggle uniforms (uTimeEnable_{id}, uVisualEnable_{id})."""
        lines = []
        for cppn_type, sig_list in (("Time", TIME_INPUTS), ("Visual", VISUAL_INPUTS)):
            for s in sig_list:
                if not s.is_spatial and s.id != "bias":
                    lines.append(f"uniform float u{cppn_type}Enable_{s.id};")
        return "\n".join(lines)

    def _glsl_base_scaling(self) -> str:
        """Generate base scaled vars (raw_time_base = u_raw_time*2-1 etc) for time."""
        lines = []
        for s in TIME_INPUTS:
            u = s._uniform()
            if u:
                lines.append(f"    float {s.id}_base = {u} * 2.0 - 1.0;")
        return "\n".join(lines)

    def _glsl_time_enable_gating(self) -> str:
        """Generate time CPPN gated input assignments."""
        lines = []
        for s in TIME_INPUTS:
            if not s.is_spatial and s.id != "bias":
                lines.append(
                    f"    float {s._glsl_var()} = {s.id}_base * uTimeEnable_{s.id};"
                )
            elif s.id == "bias":
                lines.append("    float v_bias = 1.0;")
        return "\n".join(lines)

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
{ACTIVATION_GLSL_BLOCK}"""

    def _glsl_uv_to_cppn(self) -> str:
        """Convert UV to CPPN coordinate space (-1 to 1)."""
        return """    float v_x = vUV.x * 2.0 - 1.0;
    float v_y = vUV.y * 2.0 - 1.0;
    float v_distance = sqrt(v_x * v_x + v_y * v_y);"""

    def _build_shader(self, main_body: str) -> str:
        """Build complete GLSL shader from header, main body, and color output."""
        return f"""{self._glsl_header()}

void main() {{
{main_body}

{self._get_color_output_code()}
}}
"""

    def _glsl_visual_enable_gating(self, use_time_from_network: bool) -> str:
        """Generate visual CPPN gated input assignments.

        If use_time_from_network True, time uses timeFromNetwork and others use _base
        (reassign without 'float' since time section already declared them).
        Else all use inline (uniform*2-1) for single-CPPN mode.
        """
        lines = []
        for s in VISUAL_INPUTS:
            if s.is_spatial or s.id == "bias":
                if s.id == "bias":
                    if use_time_from_network:
                        lines.append("    v_bias = 1.0;")
                    else:
                        lines.append("    float v_bias = 1.0;")
                continue
            if use_time_from_network:
                if s.id == "time":
                    src = "timeFromNetwork"
                    lines.append(
                        f"    float {s._glsl_var()} = {src} * uVisualEnable_{s.id};"
                    )
                else:
                    src = f"{s.id}_base"
                    lines.append(f"    {s._glsl_var()} = {src} * uVisualEnable_{s.id};")
            else:
                u = s._uniform()
                gvar = s._glsl_var()
                enab = f"uVisualEnable_{s.id}"
                lines.append(f"    float {gvar} = ({u} * 2.0 - 1.0) * {enab};")
        return "\n".join(lines)

    def _build_shader_template(self, node_code: str, visual_config: neat.Config) -> str:
        """Build the complete GLSL shader with node computations (single CPPN)."""
        visual_gating = self._glsl_visual_enable_gating(use_time_from_network=False)
        main_body = f"""    // Convert UV to CPPN coordinate space (-1 to 1)
{self._glsl_uv_to_cppn()}

    // Apply enable gates (disabled = 0.0 neutral)
{visual_gating}

    // Network computations
{node_code}"""
        return self._build_shader(main_body)

    def compile_dual_to_glsl(
        self,
        dual_genome: DualGenome,
        visual_config: neat.Config,
        time_config: neat.Config,
    ) -> str:
        """
        Compile a dual CPPN (time signal + visual) into GLSL shader code.

        The time signal CPPN transforms the raw time based on mouse speed,
        then the visual CPPN uses this modified time to generate colors.

        Args:
            dual_genome: DualGenome containing visual and time_signal genomes
            visual_config: NEAT configuration for visual CPPN
            time_config: NEAT configuration for time signal CPPN

        Returns:
            Complete GLSL fragment shader code as string
        """
        time_code = generate_time_signal_code(dual_genome.time_signal, time_config)
        visual_connections = get_enabled_connections(dual_genome.visual)
        visual_nodes = topological_sort(
            dual_genome.visual, visual_connections, visual_config
        )
        visual_code = generate_node_code(
            dual_genome.visual, visual_connections, visual_nodes, visual_config
        )
        return self._build_dual_shader_template(time_code, visual_code)

    def _build_dual_shader_template(self, time_code: str, visual_code: str) -> str:
        """Build the complete GLSL shader for dual CPPN (time signal + visual)."""
        base_scaling = self._glsl_base_scaling()
        time_gating = self._glsl_time_enable_gating()
        visual_gating = self._glsl_visual_enable_gating(use_time_from_network=True)
        main_body = f"""    // Raw inputs (before enable gating)
{base_scaling}

    // === TIME SIGNAL NETWORK ===
    // Apply enable gates for time CPPN inputs (disabled = 0.0 neutral)
{time_gating}

    // Time signal network computation
{time_code}

    // Get modified time from time signal network (clamped to valid range)
    float timeFromNetwork = clamp(time_output_0, -1.0, 1.0);

    // === VISUAL NETWORK ===
    // Convert UV to CPPN coordinate space (-1 to 1)
{self._glsl_uv_to_cppn()}

    // Apply enable gates for visual CPPN inputs (disabled = 0.0 neutral)
{visual_gating}

    // Visual network computations (using modified time)
{visual_code}"""
        return self._build_shader(main_body)
