"""
Shared GLSL fragments for shader compilation.

Single source for activation function definitions used in both single and dual
fragment shaders. Researchers add new NEAT activations here (and in activation.py
for CPU) when extending the compiler.
"""

# Activation function definitions for GLSL (used in shader template).
# tanh, sin, cos, abs, exp, log are GLSL built-ins and need no definition.
ACTIVATION_GLSL_BLOCK = """
// Activation functions
float sigmoid(float x) {
    return 1.0 / (1.0 + exp(-x));
}

float gauss(float x) {
    return exp(-x * x);
}

float relu(float x) {
    return max(0.0, x);
}

float square(float x) {
    return x * x;
}

float cube(float x) {
    return x * x * x;
}

float identity(float x) {
    return x;
}

float clamped(float x) {
    return clamp(x, -1.0, 1.0);
}

float hat(float x) {
    return max(0.0, 1.0 - abs(x));
}

float inv(float x) {
    if (abs(x) < 0.001) return 0.0;
    return 1.0 / x;
}
"""
