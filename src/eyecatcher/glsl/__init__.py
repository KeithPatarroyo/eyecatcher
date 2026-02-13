"""
GLSL pipeline: compile evolved CPPNs to fragment shaders for display.

This is the *output* side of the experiment: genome → GLSL. Evolution (genome,
reproduction, operators) lives in evolution/; turning a genome into shader code
lives here.
"""

from .shader_compiler import ShaderCompiler

__all__ = ["ShaderCompiler"]
