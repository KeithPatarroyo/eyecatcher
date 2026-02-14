"""
Compiles neural networks to GLSL fragment shaders.

Orchestrates topology, node code generation, and activation_registry.
Researchers extend: activation in activation_registry; output (HSV/RGB) in
_get_color_output_code; signals passed at construction.
"""

from __future__ import annotations

import neat

from ..signals.spec import SignalSpec, build_glsl_input_map
from .activation_registry import get_activation_names, get_glsl_block


class ShaderCompiler:
    """
    Compiles neural networks into GLSL fragment shader code.
    The shader can then be executed on GPU for real-time rendering.

    Args:
        visual_signals: Input signals for the visual network (from representation).
        time_signals: Input signals for the time network, or None for single-CPPN.
        derived_signals: Derived spatial inputs for visual (from representation).
        color_mode: 'hsv' (Picbreeder-style) or 'rgb' (direct RGB output)
    """

    def __init__(
        self,
        visual_signals: list,
        time_signals: list | None,
        derived_signals: list,
        color_mode: str = "hsv",
        substitutions: dict[str, str] | None = None,
    ):
        self.visual_signals = list(visual_signals)
        self.time_signals = list(time_signals) if time_signals else []
        self.derived_signals = list(derived_signals)
        self.substitutions = dict(substitutions) if substitutions else {}
        self.node_order = []
        self.node_code = {}
        self.color_mode = color_mode

    @classmethod
    def from_spec(cls, spec: SignalSpec, color_mode: str = "hsv") -> ShaderCompiler:
        """Build a ShaderCompiler from a SignalSpec.

        Reads sockets named "visual" and optionally "time" to extract signal
        lists. Falls back to the first socket for visual if no "visual" socket
        exists. Substitutions come from spec.substitutions.
        """
        try:
            visual_sock = spec.socket("visual")
        except KeyError:
            visual_sock = spec.sockets[0] if spec.sockets else None
        try:
            time_sock = spec.socket("time")
        except KeyError:
            time_sock = None
        return cls(
            visual_signals=list(visual_sock.inputs) if visual_sock else [],
            time_signals=list(time_sock.inputs) if time_sock else None,
            derived_signals=list(visual_sock.derived) if visual_sock else [],
            color_mode=color_mode,
            substitutions=spec.substitutions or None,
        )

    def with_color_mode(self, color_mode: str) -> ShaderCompiler:
        """Return a new compiler with the same signals but different color_mode."""
        return ShaderCompiler(
            self.visual_signals,
            self.time_signals,
            self.derived_signals,
            color_mode=color_mode,
            substitutions=self.substitutions,
        )

    def _toggleable_signals(self) -> list:
        """All signals that get enable toggles (deduped by id across time + visual)."""
        seen: set[str] = set()
        out: list = []
        for sig_list in (self.time_signals, self.visual_signals):
            for s in sig_list:
                if not s.is_spatial and not s.is_constant and s.id not in seen:
                    seen.add(s.id)
                    out.append(s)
        return out

    @staticmethod
    def _get_enabled_connections(
        genome: neat.DefaultGenome,
    ) -> list[tuple[int, int, float]]:
        """Return (src_id, dst_id, weight) for all enabled connections."""
        return [
            (c.key[0], c.key[1], c.weight)
            for c in genome.connections.values()
            if c.enabled
        ]

    @staticmethod
    def _topological_sort(
        genome: neat.DefaultGenome,
        connections: list[tuple[int, int, float]],
        config: neat.Config,
    ) -> list[int]:
        """
        Return node IDs in evaluation order (inputs first, then hidden, then outputs).
        Uses Kahn's algorithm.
        """
        in_degree: dict[int, int] = {}
        adjacency: dict[int, list[int]] = {}
        all_nodes: set[int] = set()

        num_inputs = config.genome_config.num_inputs
        num_outputs = config.genome_config.num_outputs
        input_nodes = list(range(-num_inputs, 0))
        output_nodes = list(range(num_outputs))

        all_nodes.update(input_nodes)
        all_nodes.update(output_nodes)
        all_nodes.update(genome.nodes.keys())

        for node in all_nodes:
            in_degree[node] = 0
            adjacency[node] = []

        for src, dst, _ in connections:
            adjacency[src].append(dst)
            in_degree[dst] += 1
            all_nodes.add(src)
            all_nodes.add(dst)

        queue = [node for node in all_nodes if in_degree[node] == 0]
        sorted_nodes: list[int] = []

        while queue:
            node = queue.pop(0)
            sorted_nodes.append(node)
            for neighbor in adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return sorted_nodes

    @staticmethod
    def _generate_node_code(
        genome: neat.DefaultGenome,
        connections: list[tuple[int, int, float]],
        nodes: list[int],
        config: neat.Config,
        input_names: dict,
        prefix: str = "",
    ) -> str:
        """Generate GLSL code for all node computations (excluding input nodes)."""
        valid_activations = set(get_activation_names())
        node_inputs: dict[int, list[tuple[int, float]]] = {}
        for src, dst, weight in connections:
            if dst not in node_inputs:
                node_inputs[dst] = []
            node_inputs[dst].append((src, weight))

        code_lines: list[str] = []
        node_vars = dict(input_names)
        num_outputs = config.genome_config.num_outputs

        for node_id in nodes:
            if node_id in input_names:
                continue

            if node_id in genome.nodes:
                node = genome.nodes[node_id]
                activation = node.activation
                bias = node.bias
                response = node.response
            else:
                activation = "identity"
                bias = 0.0
                response = 1.0

            if node_id >= num_outputs:
                var_name = f"{prefix}node_{node_id}"
            else:
                var_name = f"{prefix}output_{node_id}"
            node_vars[node_id] = var_name

            if node_id in node_inputs:
                input_terms = []
                for src_id, weight in node_inputs[node_id]:
                    src_var = node_vars.get(src_id, f"{prefix}node_{src_id}")
                    input_terms.append(f"{src_var} * {weight:.6f}")

                weighted_sum = " + ".join(input_terms)
                if bias != 0.0:
                    weighted_sum += f" + {bias:.6f}"

                activation_func = (
                    activation if activation in valid_activations else "identity"
                )

                if response != 1.0:
                    code_lines.append(
                        f"    float {var_name} = {activation_func}"
                        f"(({weighted_sum}) * {response:.6f});"
                    )
                else:
                    code_lines.append(
                        f"    float {var_name} = {activation_func}({weighted_sum});"
                    )
            else:
                code_lines.append(f"    float {var_name} = {bias:.6f};")

        return "\n".join(code_lines)

    @staticmethod
    def _generate_time_signal_code_impl(
        time_genome: neat.DefaultGenome,
        time_config: neat.Config,
        time_inputs: list,
    ) -> str:
        """Generate GLSL code for the time signal network (standalone helper)."""
        connections = ShaderCompiler._get_enabled_connections(time_genome)
        nodes = ShaderCompiler._topological_sort(time_genome, connections, time_config)
        time_input_names = build_glsl_input_map(time_inputs)
        return ShaderCompiler._generate_node_code(
            time_genome,
            connections,
            nodes,
            time_config,
            input_names=time_input_names,
            prefix="time_",
        )

    def _generate_time_signal_code(
        self,
        time_genome: neat.DefaultGenome,
        time_config: neat.Config,
    ) -> str:
        """Generate GLSL code for the time signal network using self.time_signals."""
        return ShaderCompiler._generate_time_signal_code_impl(
            time_genome, time_config, self.time_signals
        )

    def compile(
        self,
        visual_genome: neat.DefaultGenome,
        visual_config: neat.Config,
        time_genome: neat.DefaultGenome | None = None,
        time_config: neat.Config | None = None,
    ) -> str:
        """
        Compile visual (and optionally time) genomes into GLSL shader code.

        Single-CPPN: pass visual_genome and visual_config only.
        Dual-CPPN: pass visual_genome, visual_config, time_genome, and time_config.
        The representation is responsible for passing the correct arguments.

        Args:
            visual_genome: NEAT genome for the visual network
            visual_config: NEAT configuration for the visual network
            time_genome: Optional genome for the time signal network (dual-CPPN)
            time_config: NEAT config for time network, or None for single-CPPN

        Returns:
            Complete GLSL fragment shader code as string
        """
        if time_config is not None and time_genome is not None:
            time_code = self._generate_time_signal_code(time_genome, time_config)
        else:
            time_code = None

        connections = self._get_enabled_connections(visual_genome)
        nodes = self._topological_sort(visual_genome, connections, visual_config)
        visual_code = self._generate_node_code(
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
        """Generate enable toggle uniforms (uEnable_{id}), one per toggleable signal."""
        lines = []
        for s in self._toggleable_signals():
            lines.append(f"uniform float uEnable_{s.id};")
        return "\n".join(lines)

    def _glsl_enable_gating(self, signals: list, base_vars: bool = True) -> str:
        """Generate gated input assignments for a signal list (time or visual)."""
        lines = []
        for s in signals:
            if s.is_constant:
                lines.append(f"    float {s._glsl_var()} = {s.default};")
            elif not s.is_spatial:
                val = f"{s.id}_base" if base_vars else f"({s._uniform()} * 2.0 - 1.0)"
                lines.append(f"    float {s._glsl_var()} = {val} * uEnable_{s.id};")
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
        return self._glsl_enable_gating(self.time_signals, base_vars=True)

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

        When use_time_from_network is True (dual-CPPN), derived signals use
        substitutions (e.g. time -> timeFromNetwork). Others use _base where
        already declared in time section, else inline (uniform*2-1).
        """
        lines = []
        time_ids = {t.id for t in self.time_signals}
        for s in self.visual_signals:
            if s.is_spatial:
                continue
            if s.is_constant:
                if use_time_from_network and s.id in time_ids:
                    lines.append(f"    {s._glsl_var()} = {s.default};")
                else:
                    lines.append(f"    float {s._glsl_var()} = {s.default};")
                continue
            if use_time_from_network and s.id in self.substitutions:
                expr = f"{self.substitutions[s.id]} * uEnable_{s.id}"
                lines.append(f"    float {s._glsl_var()} = {expr};")
                continue
            u = s._uniform()
            expr = f"({u} * 2.0 - 1.0) * uEnable_{s.id}"
            if use_time_from_network and s.id in time_ids:
                lines.append(f"    {s._glsl_var()} = {expr};")
            else:
                lines.append(f"    float {s._glsl_var()} = {expr};")
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
