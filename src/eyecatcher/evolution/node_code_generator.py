"""
Node code generation: genome + config + signal map -> GLSL node computations.

Used by ShaderCompiler. Input ordering and variable names come from signals.py.
Add activations in ACTIVATION_FUNCTIONS and glsl_fragments.ACTIVATION_GLSL_BLOCK.
"""

from typing import Optional

import neat

from .compiler_topology import get_enabled_connections, topological_sort
from .signals import TIME_INPUTS, VISUAL_INPUTS, build_glsl_input_map

# NEAT activation name -> GLSL name (must exist in glsl_fragments).
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


def generate_node_code(
    genome: neat.DefaultGenome,
    connections: list[tuple[int, int, float]],
    nodes: list[int],
    config: neat.Config,
    input_names: Optional[dict] = None,
    prefix: str = "",
) -> str:
    """Generate GLSL code for all node computations (excluding input nodes)."""
    node_inputs: dict[int, list[tuple[int, float]]] = {}
    for src, dst, weight in connections:
        if dst not in node_inputs:
            node_inputs[dst] = []
        node_inputs[dst].append((src, weight))

    code_lines: list[str] = []
    if input_names is None:
        input_names = build_glsl_input_map(VISUAL_INPUTS)

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

            activation_func = ACTIVATION_FUNCTIONS.get(activation, "identity")

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


def generate_time_signal_code(
    time_genome: neat.DefaultGenome, time_config: neat.Config
) -> str:
    """Generate GLSL code for the time signal CPPN."""
    connections = get_enabled_connections(time_genome)
    nodes = topological_sort(time_genome, connections, time_config)
    time_input_names = build_glsl_input_map(TIME_INPUTS)
    return generate_node_code(
        time_genome,
        connections,
        nodes,
        time_config,
        input_names=time_input_names,
        prefix="time_",
    )
