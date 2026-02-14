"""
Node code generation: genome + config + signal map -> GLSL node computations.

Implementation lives in ShaderCompiler; this module re-exports for backward
compatibility. Prefer using ShaderCompiler directly.
"""

from .shader_compiler import ShaderCompiler

generate_node_code = ShaderCompiler._generate_node_code
generate_time_signal_code = ShaderCompiler._generate_time_signal_code_impl
