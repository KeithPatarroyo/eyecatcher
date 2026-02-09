"""
CPPN to GLSL Shader Compiler.
Converts NEAT genomes into GPU-executable shader code.

Supports dual-CPPN compilation where a time signal CPPN modulates
the time input to a visual CPPN.
"""

import json
from typing import TYPE_CHECKING, Optional

import neat

if TYPE_CHECKING:
    from .cppn_engine import DualGenome


class ShaderCompiler:
    """
    Compiles CPPN networks into GLSL fragment shader code.
    The shader can then be executed on GPU for real-time rendering.

    Args:
        color_mode: 'hsv' (Picbreeder-style) or 'rgb' (direct RGB output)
    """

    # Map NEAT activation functions to GLSL
    ACTIVATION_FUNCTIONS = {
        "sigmoid": "sigmoid",
        "tanh": "tanh",
        "sin": "sin",
        "cos": "cos",
        "gauss": "gauss",
        "relu": "relu",
        "abs": "abs",
        "square": "square",
        "cube": "cube",
        "identity": "identity",
        "clamped": "clamped",
        "exp": "exp",
        "hat": "hat",
        "inv": "inv",
        "log": "log",
    }

    def __init__(self, color_mode: str = "hsv"):
        self.node_order: list[int] = []
        self.node_code: dict[int, str] = {}
        self.color_mode = color_mode  # 'hsv' or 'rgb'

    def compile_to_glsl(self, genome: neat.DefaultGenome, config: neat.Config) -> str:
        """
        Compile a CPPN genome into GLSL shader code.

        Args:
            genome: NEAT genome to compile
            config: NEAT configuration

        Returns:
            Complete GLSL fragment shader code as string
        """
        # Analyze network topology
        connections = self._get_enabled_connections(genome)
        nodes = self._topological_sort(genome, connections, config)

        # Generate node computation code
        node_computations = self._generate_node_code(genome, connections, nodes, config)

        # Build complete shader
        shader = self._build_shader_template(node_computations, config)

        return shader

    def _get_enabled_connections(self, genome: neat.DefaultGenome) -> list[tuple]:
        """Get all enabled connections in the genome."""
        return [
            (c.key[0], c.key[1], c.weight)
            for c in genome.connections.values()
            if c.enabled
        ]

    def _topological_sort(
        self, genome: neat.DefaultGenome, connections: list[tuple], config: neat.Config
    ) -> list[int]:
        """
        Topologically sort nodes for correct evaluation order.

        Returns:
            List of node IDs in evaluation order
        """
        # Build adjacency list
        in_degree = {}
        adjacency = {}
        all_nodes = set()

        # Initialize with input nodes (IDs 0-4: x, y, distance, time, bias)
        num_inputs = config.genome_config.num_inputs
        input_nodes = list(range(-num_inputs, 0))

        # Output nodes (IDs starting from 0: R, G, B)
        num_outputs = config.genome_config.num_outputs
        output_nodes = list(range(num_outputs))

        all_nodes.update(input_nodes)
        all_nodes.update(output_nodes)
        all_nodes.update(genome.nodes.keys())

        # Initialize in-degree and adjacency
        for node in all_nodes:
            in_degree[node] = 0
            adjacency[node] = []

        # Build graph from connections
        for src, dst, weight in connections:
            adjacency[src].append(dst)
            in_degree[dst] += 1
            all_nodes.add(src)
            all_nodes.add(dst)

        # Topological sort using Kahn's algorithm
        queue = [node for node in all_nodes if in_degree[node] == 0]
        sorted_nodes = []

        while queue:
            node = queue.pop(0)
            sorted_nodes.append(node)

            for neighbor in adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return sorted_nodes

    def _generate_node_code(
        self,
        genome: neat.DefaultGenome,
        connections: list[tuple],
        nodes: list[int],
        config: neat.Config,
        input_names: Optional[dict[int, str]] = None,
        prefix: str = "",
    ) -> str:
        """Generate GLSL code for all node computations."""

        # Build connection map: node_id -> [(input_node, weight), ...]
        node_inputs = {}
        for src, dst, weight in connections:
            if dst not in node_inputs:
                node_inputs[dst] = []
            node_inputs[dst].append((src, weight))

        code_lines = []

        # Default input names for visual CPPN (8 inputs)
        if input_names is None:
            input_names = {
                -8: "vX",
                -7: "vY",
                -6: "vDist",
                -5: "vTime",
                -4: "vMouseSpeed",
                -3: "vMouseDist",
                -2: "vInactivity",
                -1: "vBias",
            }

        node_vars = input_names.copy()

        # Generate code for each node
        for node_id in nodes:
            # Skip input nodes (already defined)
            if node_id in input_names:
                continue

            # Get node configuration
            if node_id in genome.nodes:
                node = genome.nodes[node_id]
                activation = node.activation
                bias = node.bias
                response = node.response
            else:
                # Output nodes use defaults
                activation = "identity"
                bias = 0.0
                response = 1.0

            # Generate variable name with optional prefix
            if node_id >= config.genome_config.num_outputs:
                var_name = f"{prefix}node_{node_id}"
            else:
                var_name = f"{prefix}output_{node_id}"
            node_vars[node_id] = var_name

            # Compute weighted sum of inputs
            if node_id in node_inputs:
                input_terms = []
                for src_id, weight in node_inputs[node_id]:
                    src_var = node_vars.get(src_id, f"{prefix}node_{src_id}")
                    input_terms.append(f"{src_var} * {weight:.6f}")

                weighted_sum = " + ".join(input_terms)
                if bias != 0.0:
                    weighted_sum += f" + {bias:.6f}"

                # Apply activation function
                activation_func = self.ACTIVATION_FUNCTIONS.get(activation, "identity")

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
                # Node with no inputs
                code_lines.append(f"    float {var_name} = {bias:.6f};")

        return "\n".join(code_lines)

    def _generate_time_signal_code(
        self, time_genome: neat.DefaultGenome, time_config: neat.Config
    ) -> str:
        """Generate GLSL code for the time signal CPPN."""
        connections = self._get_enabled_connections(time_genome)
        nodes = self._topological_sort(time_genome, connections, time_config)

        # Time signal: raw_time, mouseSpeed, mouseDistance, activity, bias (5 inputs)
        time_input_names = {
            -5: "vRawTime",
            -4: "vMouseSpeed",
            -3: "vMouseDist",
            -2: "vInactivity",
            -1: "vBias",
        }

        return self._generate_node_code(
            time_genome,
            connections,
            nodes,
            time_config,
            input_names=time_input_names,
            prefix="time_",
        )

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

    def _build_shader_template(self, node_code: str, config: neat.Config) -> str:
        """Build the complete GLSL shader with node computations (single CPPN)."""

        color_output = self._get_color_output_code()

        shader = f"""#version 300 es
precision highp float;

// Inputs from vertex shader
in vec2 vUV;  // UV coordinates (0-1)
uniform float uTime;  // Time uniform (0-1)
uniform float uMouseSpeed;  // Mouse movement speed (0-1)
uniform float uMouseDist;  // Distance from mouse to this pattern's center (0-1)
uniform float uInactivity;  // Activity: boosted by speed, decays when still (0-1)

// Signal enable toggles (0.0 = disabled/neutral, 1.0 = enabled)
uniform float uTimeEnableRawTime;
uniform float uTimeEnableMouseSpeed;
uniform float uTimeEnableMouseDist;
uniform float uTimeEnableInactivity;
uniform float uVisualEnableTime;
uniform float uVisualEnableMouseSpeed;
uniform float uVisualEnableMouseDist;
uniform float uVisualEnableInactivity;

// Output color
out vec4 fragColor;

// Activation functions
float sigmoid(float x) {{
    return 1.0 / (1.0 + exp(-x));
}}

float gauss(float x) {{
    return exp(-x * x);
}}

float relu(float x) {{
    return max(0.0, x);
}}

float square(float x) {{
    return x * x;
}}

float cube(float x) {{
    return x * x * x;
}}

float identity(float x) {{
    return x;
}}

float clamped(float x) {{
    return clamp(x, -1.0, 1.0);
}}

float hat(float x) {{
    return max(0.0, 1.0 - abs(x));
}}

float inv(float x) {{
    if (abs(x) < 0.001) return 0.0;
    return 1.0 / x;
}}

void main() {{
    // Convert UV to CPPN coordinate space (-1 to 1)
    float vX = vUV.x * 2.0 - 1.0;
    float vY = vUV.y * 2.0 - 1.0;
    float vDist = sqrt(vX * vX + vY * vY);

    // Apply enable gates (disabled = 0.0 neutral)
    float vTime = (uTime * 2.0 - 1.0) * uVisualEnableTime;
    float vMouseSpeed = (uMouseSpeed * 2.0 - 1.0) * uVisualEnableMouseSpeed;
    float vMouseDist = (uMouseDist * 2.0 - 1.0) * uVisualEnableMouseDist;
    float vInactivity = (uInactivity * 2.0 - 1.0) * uVisualEnableInactivity;
    float vBias = 1.0;

    // Network computations
{node_code}

{color_output}
}}
"""
        return shader

    def compile_dual_to_glsl(
        self,
        dual_genome: "DualGenome",
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
        # Generate time signal network code
        time_code = self._generate_time_signal_code(
            dual_genome.time_signal, time_config
        )

        # Generate visual network code
        visual_connections = self._get_enabled_connections(dual_genome.visual)
        visual_nodes = self._topological_sort(
            dual_genome.visual, visual_connections, visual_config
        )
        visual_code = self._generate_node_code(
            dual_genome.visual, visual_connections, visual_nodes, visual_config
        )

        # Build the dual shader
        shader = self._build_dual_shader_template(time_code, visual_code)

        return shader

    def _build_dual_shader_template(self, time_code: str, visual_code: str) -> str:
        """Build the complete GLSL shader for dual CPPN (time signal + visual)."""

        color_output = self._get_color_output_code()

        shader = f"""#version 300 es
precision highp float;

// Inputs from vertex shader
in vec2 vUV;  // UV coordinates (0-1)
uniform float uTime;  // Time uniform (0-1)
uniform float uMouseSpeed;  // Mouse movement speed (0-1)
uniform float uMouseDist;  // Distance from mouse to this pattern's center (0-1)
uniform float uInactivity;  // Activity: boosted by speed, decays when still (0-1)

// Signal enable toggles (0.0 = disabled/neutral, 1.0 = enabled)
uniform float uTimeEnableRawTime;
uniform float uTimeEnableMouseSpeed;
uniform float uTimeEnableMouseDist;
uniform float uTimeEnableInactivity;
uniform float uVisualEnableTime;
uniform float uVisualEnableMouseSpeed;
uniform float uVisualEnableMouseDist;
uniform float uVisualEnableInactivity;

// Output color
out vec4 fragColor;

// Activation functions
float sigmoid(float x) {{
    return 1.0 / (1.0 + exp(-x));
}}

float gauss(float x) {{
    return exp(-x * x);
}}

float relu(float x) {{
    return max(0.0, x);
}}

float square(float x) {{
    return x * x;
}}

float cube(float x) {{
    return x * x * x;
}}

float identity(float x) {{
    return x;
}}

float clamped(float x) {{
    return clamp(x, -1.0, 1.0);
}}

float hat(float x) {{
    return max(0.0, 1.0 - abs(x));
}}

float inv(float x) {{
    if (abs(x) < 0.001) return 0.0;
    return 1.0 / x;
}}

void main() {{
    // Raw inputs (before enable gating)
    float rawTime_base = uTime * 2.0 - 1.0;
    float mouseSpeed_base = uMouseSpeed * 2.0 - 1.0;
    float mouseDist_base = uMouseDist * 2.0 - 1.0;
    float inactivity_base = uInactivity * 2.0 - 1.0;
    float vBias = 1.0;

    // === TIME SIGNAL NETWORK ===
    // Apply enable gates for time CPPN inputs (disabled = 0.0 neutral)
    float vRawTime = rawTime_base * uTimeEnableRawTime;
    float vMouseSpeed = mouseSpeed_base * uTimeEnableMouseSpeed;
    float vMouseDist = mouseDist_base * uTimeEnableMouseDist;
    float vInactivity = inactivity_base * uTimeEnableInactivity;

    // Time signal network computation
{time_code}

    // Get modified time from time signal network (clamped to valid range)
    float timeFromNetwork = clamp(time_output_0, -1.0, 1.0);

    // === VISUAL NETWORK ===
    // Convert UV to CPPN coordinate space (-1 to 1)
    float vX = vUV.x * 2.0 - 1.0;
    float vY = vUV.y * 2.0 - 1.0;
    float vDist = sqrt(vX * vX + vY * vY);

    // Apply enable gates for visual CPPN inputs (disabled = 0.0 neutral)
    float vTime = timeFromNetwork * uVisualEnableTime;
    vMouseSpeed = mouseSpeed_base * uVisualEnableMouseSpeed;
    vMouseDist = mouseDist_base * uVisualEnableMouseDist;
    vInactivity = inactivity_base * uVisualEnableInactivity;

    // Visual network computations (using modified time)
{visual_code}

{color_output}
}}
"""
        return shader

    def export_shader_bundle(
        self, genome: neat.DefaultGenome, config: neat.Config, filepath: str
    ):
        """
        Export shader code and metadata as a JSON bundle.

        Args:
            genome: NEAT genome
            config: NEAT configuration
            filepath: Output file path
        """
        shader_code = self.compile_to_glsl(genome, config)

        bundle = {
            "shader": shader_code,
            "metadata": {
                "num_nodes": len(genome.nodes),
                "num_connections": len(
                    [c for c in genome.connections.values() if c.enabled]
                ),
                "fitness": getattr(genome, "fitness", None),
            },
        }

        with open(filepath, "w") as f:
            json.dump(bundle, f, indent=2)

    def export_dual_shader_bundle(
        self,
        dual_genome: "DualGenome",
        visual_config: neat.Config,
        time_config: neat.Config,
        filepath: str,
    ):
        """
        Export dual CPPN shader code and metadata as a JSON bundle.

        Args:
            dual_genome: DualGenome containing visual and time_signal genomes
            visual_config: NEAT configuration for visual CPPN
            time_config: NEAT configuration for time signal CPPN
            filepath: Output file path
        """
        shader_code = self.compile_dual_to_glsl(dual_genome, visual_config, time_config)

        bundle = {
            "shader": shader_code,
            "metadata": {
                "type": "dual_cppn",
                "visual": {
                    "num_nodes": len(dual_genome.visual.nodes),
                    "num_connections": len(
                        [
                            c
                            for c in dual_genome.visual.connections.values()
                            if c.enabled
                        ]
                    ),
                },
                "time_signal": {
                    "num_nodes": len(dual_genome.time_signal.nodes),
                    "num_connections": len(
                        [
                            c
                            for c in dual_genome.time_signal.connections.values()
                            if c.enabled
                        ]
                    ),
                },
                "fitness": dual_genome.fitness,
            },
        }

        with open(filepath, "w") as f:
            json.dump(bundle, f, indent=2)
