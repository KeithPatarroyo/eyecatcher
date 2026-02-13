"""
Shared GLSL fragments for shader compilation.

Activation block is built from the canonical registry in activation_registry.py.
Researchers add new NEAT activations there; GLSL and JS stay in sync via tests/codegen.
"""

from .activation_registry import get_glsl_block

ACTIVATION_GLSL_BLOCK = get_glsl_block()
