"""Optional tests that validate compiled GLSL with an external validator.

If glslangValidator (Vulkan SDK / glslang) is on PATH, run it on substrate-compiled
fragment shaders to catch WebGL compile errors. Skip if the binary is not found.
Run with: pytest tests/test_glsl_compile_external.py -v
Exclude slow tests: pytest -m "not slow"
"""

import shutil
import subprocess
import tempfile

import pytest
from eyecatcher.substrate import (
    ElementaryCASubstrate,
)


def _glslang_available() -> bool:
    return shutil.which("glslangValidator") is not None


def _validate_fragment_shader(glsl: str) -> tuple[bool, str]:
    """Run glslangValidator -S frag on the shader. Return (ok, stderr)."""
    cmd = shutil.which("glslangValidator")
    if not cmd:
        return True, ""  # skip
    with tempfile.NamedTemporaryFile(mode="w", suffix=".frag", delete=False) as f:
        f.write(glsl)
        path = f.name
    try:
        result = subprocess.run(
            [cmd, "-S", "frag", path],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0, result.stderr or result.stdout or ""
    finally:
        import os

        try:
            os.unlink(path)
        except OSError:
            pass


@pytest.mark.slow
def test_ca_compiled_shader_valid_glsl():
    """CA substrate compiled shader passes glslangValidator (if available)."""
    substrate = ElementaryCASubstrate(width=64, generations=32)
    ind = substrate.create_random(key=0)
    glsl = substrate.compile_to_shader(ind)
    assert glsl is not None and "void main()" in glsl
    ok, err = _validate_fragment_shader(glsl)
    if not _glslang_available():
        pytest.skip("glslangValidator not on PATH (install Vulkan SDK or glslang)")
    assert ok, f"glslangValidator failed:\n{err}"


@pytest.mark.slow
def test_dual_cppn_compiled_shader_valid_glsl(dual_cppn_substrate, random_dual_genome):
    """Dual CPPN compiled shader passes glslangValidator (if available)."""
    glsl = dual_cppn_substrate.compile_to_shader(random_dual_genome)
    assert glsl is not None and "void main()" in glsl
    ok, err = _validate_fragment_shader(glsl)
    if not _glslang_available():
        pytest.skip("glslangValidator not on PATH (install Vulkan SDK or glslang)")
    assert ok, f"glslangValidator failed:\n{err}"
