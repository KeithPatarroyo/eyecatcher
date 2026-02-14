"""
Topology helpers for shader compilation: enabled connections and evaluation order.

Implementation lives in ShaderCompiler; this module re-exports for backward
compatibility. Prefer using ShaderCompiler directly.
"""

from .shader_compiler import ShaderCompiler

get_enabled_connections = ShaderCompiler._get_enabled_connections
topological_sort = ShaderCompiler._topological_sort
