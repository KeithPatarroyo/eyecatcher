"""Tests for representation refactor: NeatEvolvable, GridBase, parse_express_options."""

from eyecatcher.representation import (
    ConwayRepresentation,
    NCARepresentation,
    SingleCPPNRepresentation,
)
from eyecatcher.representation.grid_base import GridRepresentationBase
from eyecatcher.representation.mixins import NeatEvolvable


def test_single_cppn_inherits_neat_evolvable_and_sets_key():
    """SingleCPPN uses NeatEvolvable; create_random sets genome.key."""
    rep = SingleCPPNRepresentation()
    assert isinstance(rep, NeatEvolvable)
    genome = rep.create_random(key=7)
    assert genome.key == 7


def test_nca_inherits_neat_evolvable_and_sets_key():
    """NCA uses NeatEvolvable; create_random sets genome.key."""
    rep = NCARepresentation()
    assert isinstance(rep, NeatEvolvable)
    genome = rep.create_random(key=11)
    assert genome.key == 11


def test_conway_inherits_grid_base():
    """ConwayRepresentation inherits GridRepresentationBase."""
    rep = ConwayRepresentation()
    assert isinstance(rep, GridRepresentationBase)
    filenames = rep.get_save_filenames(individual_id=1)
    assert "png" in filenames and "genome_json" in filenames


def test_nca_inherits_grid_base():
    """NCARepresentation inherits GridRepresentationBase."""
    rep = NCARepresentation()
    assert isinstance(rep, GridRepresentationBase)


def test_parse_express_options_base_returns_empty():
    """RepresentationBase.parse_express_options returns {} by default."""
    # Use a concrete class that doesn't override it (e.g. Conway has default from base)
    rep = ConwayRepresentation()
    assert rep.parse_express_options({}) == {}
    assert rep.parse_express_options({"nca_steps": 5}) == {}


def test_parse_express_options_nca_allowlists_options():
    """NCA.parse_express_options allowlists nca_steps and nca_preview_grid_size."""
    rep = NCARepresentation()
    out = rep.parse_express_options({})
    assert out == {}

    out = rep.parse_express_options({"nca_steps": 10})
    assert out == {"nca_steps": 10}

    out = rep.parse_express_options({"nca_preview_grid_size": 24})
    assert out == {"nca_preview_grid_size": 24}

    out = rep.parse_express_options(
        {"nca_steps": 5, "nca_preview_grid_size": 16, "other": "ignored"}
    )
    assert out["nca_steps"] == 5
    assert out["nca_preview_grid_size"] == 16
    assert "other" not in out


def test_parse_express_options_nca_clamps_values():
    """NCA clamps nca_steps >= 1 and nca_preview_grid_size >= 8."""
    rep = NCARepresentation()
    out = rep.parse_express_options({"nca_steps": 0})
    assert out["nca_steps"] == 1
    out = rep.parse_express_options({"nca_preview_grid_size": 4})
    assert out["nca_preview_grid_size"] == 8
