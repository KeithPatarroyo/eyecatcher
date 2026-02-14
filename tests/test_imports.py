"""Test that all major imports work correctly."""


def test_canonical_package_imports():
    """Test that evolution, genome, glsl, representation export the main API."""
    from eyecatcher.evolution import produce_next_generation
    from eyecatcher.genome import (
        DualGenome,
        create_random_dual_genome,
        dual_genome_to_json,
    )
    from eyecatcher.glsl import ShaderCompiler
    from eyecatcher.representation import DualCPPNRepresentation, get_representation

    assert produce_next_generation is not None
    assert DualCPPNRepresentation is not None
    assert DualGenome is not None
    assert create_random_dual_genome is not None
    assert dual_genome_to_json is not None
    assert get_representation is not None
    assert ShaderCompiler is not None


def test_new_submodule_imports():
    """Test that new submodules are importable directly."""
    from eyecatcher.genome import DualGenome
    from eyecatcher.inspection import render_genome_network_pdf
    from eyecatcher.representation import DualCPPNRepresentation
    from eyecatcher.signals import SignalSpec, catalog

    assert DualCPPNRepresentation is not None
    assert DualGenome is not None
    assert catalog.DUAL_CPPN_VISUAL_INPUTS is not None
    assert SignalSpec is not None
    assert render_genome_network_pdf is not None
    representation = DualCPPNRepresentation()
    assert callable(getattr(representation, "render_to_image", None))
    assert hasattr(representation, "signal_spec")


def test_signal_catalog_imports():
    """Test that signal catalog and spec are importable."""
    from eyecatcher.signals import Socket, catalog
    from eyecatcher.signals.spec import (
        DerivedInput,
        Output,
        Signal,
        SignalSpec,
    )

    assert Signal is not None
    assert Output is not None
    assert DerivedInput is not None
    assert SignalSpec is not None
    assert Socket is not None
    assert len(catalog.SPATIAL) > 0
    assert len(catalog.INTERACTION) > 0
    assert len(catalog.RGB_OUTPUTS) == 3


def test_socket_subclass_imports():
    """Test that Socket subclasses are importable from representation.sockets."""
    from eyecatcher.representation.sockets import GridSocket, NeatSocket
    from eyecatcher.signals import Socket

    assert issubclass(NeatSocket, Socket)
    assert issubclass(GridSocket, Socket)


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
