"""
Assemble NEAT NetworkContribution into an NCA step shader.

Produces a complete fragment shader: Sobel perception, NEAT network evaluation,
stochastic update, alive masking, and state clamp. Used by NCARepresentation.develop().
"""

from __future__ import annotations

from ..representation.receptors import NetworkContribution
from .activation_registry import get_glsl_block
from .codegen import generate_node_code


def assemble_nca_step_shader(contribution: NetworkContribution) -> str:
    """Produce a complete NCA step shader from a compiled NEAT network contribution.

    Expects contribution with 14 inputs (12 perception + raw_time + mouse_cell_dist)
    and 4 outputs (state delta). Emits: uniforms, getState(), Sobel perception,
    input variable assignments, NEAT node code, stochastic mask, alive mask, clamp.
    """
    node_code = generate_node_code(contribution)
    assert contribution.num_outputs == 4, "NCA requires 4 outputs (state delta)"

    perception_and_signals = """
    vec4 self_ = getState(vec2(0.0, 0.0));
    vec4 tl = getState(vec2(-1.0, -1.0));
    vec4 tc = getState(vec2(0.0, -1.0));
    vec4 tr = getState(vec2(1.0, -1.0));
    vec4 ml = getState(vec2(-1.0, 0.0));
    vec4 mr = getState(vec2(1.0, 0.0));
    vec4 bl = getState(vec2(-1.0, 1.0));
    vec4 bc = getState(vec2(0.0, 1.0));
    vec4 br = getState(vec2(1.0, 1.0));

    vec4 grad_x = (tr + 2.0 * mr + br) - (tl + 2.0 * ml + bl);
    vec4 grad_y = (bl + 2.0 * bc + br) - (tl + 2.0 * tc + tr);

    float v_nca_self_r = self_.r;
    float v_nca_self_g = self_.g;
    float v_nca_self_b = self_.b;
    float v_nca_self_a = self_.a;
    float v_nca_dx_r = grad_x.r;
    float v_nca_dx_g = grad_x.g;
    float v_nca_dx_b = grad_x.b;
    float v_nca_dx_a = grad_x.a;
    float v_nca_dy_r = grad_y.r;
    float v_nca_dy_g = grad_y.g;
    float v_nca_dy_b = grad_y.b;
    float v_nca_dy_a = grad_y.a;
    float v_raw_time = u_raw_time;
    float v_mouse_cell_dist = length(vUV - vec2(u_mouse_x, u_mouse_y));
"""

    main_body = f"""
void main() {{
    // === PERCEPTION (Sobel) ===
{perception_and_signals}

    // === NEAT NETWORK (state delta) ===
{node_code}

    vec4 ds = vec4(output_0, output_1, output_2, output_3);

    // Stochastic update mask
    float rand = fract(sin(dot(vUV + u_raw_time, vec2(12.9898, 78.233))) * 43758.5453);
    ds *= step(0.5, rand);

    vec4 newState = self_ + ds;

    // Alive masking
    float maxAlpha = max(
        max(max(max(tl.a, tc.a), max(tr.a, ml.a)), max(mr.a, max(bl.a, bc.a))),
        max(br.a, self_.a));
    if (maxAlpha < 0.1) newState = vec4(0.0);

    fragColor = clamp(newState, -1.0, 1.0);
}}
"""

    header = (
        """#version 300 es
precision highp float;

uniform sampler2D u_state;
uniform vec2 u_texelSize;
uniform float u_raw_time;
uniform float u_mouse_x;
uniform float u_mouse_y;

in vec2 vUV;
out vec4 fragColor;

vec4 getState(vec2 offset) {
    return texture(u_state, vUV + offset * u_texelSize);
}

"""
        + get_glsl_block()
        + "\n"
    )

    return header + main_body
