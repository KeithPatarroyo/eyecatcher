"""
Generate rendering code from network contributions.

Takes opaque NetworkContribution (from NeatReceptor.compile) and produces
the node computation code string. Used by RuleAssembler.
"""

from __future__ import annotations

from ..representation.receptors import NetworkContribution
from .activation_registry import get_activation_names


def generate_node_code(contribution: NetworkContribution) -> str:
    """Generate code for all node computations (excluding input nodes)."""
    valid_activations = set(get_activation_names())
    node_inputs: dict[int, list[tuple[int, float]]] = {}
    for src, dst, weight in contribution.connections:
        if dst not in node_inputs:
            node_inputs[dst] = []
        node_inputs[dst].append((src, weight))

    code_lines: list[str] = []
    node_vars = dict(contribution.input_map)
    prefix = contribution.prefix
    num_outputs = contribution.num_outputs

    for node_id in contribution.node_order:
        if node_id in contribution.input_map:
            continue

        activation, bias, response = contribution.node_data.get(
            node_id, ("identity", 0.0, 1.0)
        )

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
