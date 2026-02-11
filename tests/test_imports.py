"""Test that all major imports work correctly."""


def test_canonical_package_imports():
    """Test that algorithm, genome, glsl export the main API."""
    from eyecatcher.algorithm import CPPNEngine
    from eyecatcher.genome import (
        DualGenome,
        create_random_dual_genome,
        dual_genome_to_json,
    )
    from eyecatcher.glsl import ShaderCompiler

    assert CPPNEngine is not None
    assert DualGenome is not None
    assert create_random_dual_genome is not None
    assert dual_genome_to_json is not None
    assert ShaderCompiler is not None


def test_new_submodule_imports():
    """Test that new submodules are importable directly."""
    from eyecatcher.algorithm import CPPNEngine
    from eyecatcher.evaluation import render_dual_image
    from eyecatcher.genome import DualGenome
    from eyecatcher.signals import VISUAL_INPUTS

    assert CPPNEngine is not None
    assert DualGenome is not None
    assert VISUAL_INPUTS is not None
    assert render_dual_image is not None


def test_web_imports():
    """Test that web module imports work."""
    from eyecatcher.web import app

    assert app is not None


def test_data_imports():
    """Test that data layer imports work."""
    from eyecatcher.data.genealogy_db import (
        save_generation_result,
        save_population,
    )

    assert save_generation_result is not None
    assert save_population is not None


def test_server_imports():
    """Test that server can be imported (catches module-level errors)."""
    from eyecatcher.server import app

    assert app is not None
