"""Tests for sensory system (signals), catalog, and config alignment."""

import json
import os

import pytest
from eyecatcher import get_root_dir
from eyecatcher.representation import DualCPPNRepresentation
from eyecatcher.signals import catalog, export_for_frontend


def test_neat_config_matches_representation(representation):
    """NEAT config num_inputs/num_outputs match receptor signal counts."""
    assert representation.config.genome_config.num_inputs == len(
        representation.visual.inputs
    )
    assert representation.config.genome_config.num_outputs == len(
        representation.visual.outputs
    )
    assert representation.time_config.genome_config.num_inputs == len(
        representation.time.inputs
    )
    assert representation.time_config.genome_config.num_outputs == len(
        representation.time.outputs
    )


def test_signals_export_for_frontend():
    """export_for_frontend returns expected keys (SIGNAL_GROUPS, OUTPUTS, etc.)."""
    rep = DualCPPNRepresentation()
    data = export_for_frontend(rep.sensory_system)
    assert "SIGNAL_GROUPS" in data
    assert "TOGGLEABLE_SIGNALS" in data
    assert "OUTPUTS" in data
    assert "SIGNAL_IDS" in data
    groups = data["SIGNAL_GROUPS"]
    assert any(g.get("label") in ("Spatial", "Temporal", "Interaction") for g in groups)
    assert data["OUTPUTS"] == [
        {"id": "red", "label": "Red"},
        {"id": "green", "label": "Green"},
        {"id": "blue", "label": "Blue"},
    ]
    assert set(data["SIGNAL_IDS"]) >= {
        "activity",
        "mouse_dist",
        "mouse_speed",
        "mouse_x",
        "mouse_y",
    }


def _load_generated_config():
    """Parse config.generated.js and return the config object."""
    root = get_root_dir()
    js_path = os.path.join(root, "static", "js", "config.generated.js")
    if not os.path.isfile(js_path):
        return None
    with open(js_path, encoding="utf-8") as f:
        text = f.read()
    start = text.find("window.EyecatcherConfig = ")
    if start < 0:
        return None
    start = text.index("{", start)
    depth = 0
    end = start
    for i, c in enumerate(text[start:], start):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    return json.loads(text[start : end + 1])


def test_frontend_signals_match_backend():
    """Generated config has signals by representation id; dual_cppn matches backend."""
    config = _load_generated_config()
    if config is None:
        pytest.skip("run make generate to create generated file")
    signals = config.get("signals", {})
    assert isinstance(signals, dict), "signals should be keyed by representation id"
    assert "dual_cppn" in signals
    data = signals["dual_cppn"]
    rep = DualCPPNRepresentation()
    expected = export_for_frontend(rep.sensory_system)
    assert set(data["SIGNAL_IDS"]) == set(expected["SIGNAL_IDS"])
    assert "TOGGLEABLE_SIGNALS" in data
    assert "SIGNAL_GROUPS" in data


def test_generated_signals_file_is_up_to_date():
    """Generated config signals: one entry per representation, each matching backend.

    If this fails, run `make generate` and commit.
    """
    from eyecatcher.representation.registry import REPRESENTATIONS, get_representation

    config = _load_generated_config()
    if config is None:
        pytest.skip("run make generate to create generated file")
    generated = config.get("signals", {})
    expected = {}
    for rid in REPRESENTATIONS:
        rep = get_representation(rid)
        expected[rid] = export_for_frontend(rep.sensory_system)
    assert (
        generated == expected
    ), "config.generated.js signals section is out of date. Run: make generate"


# ---------------------------------------------------------------
# SensorySystem tests
# ---------------------------------------------------------------


class TestSensorySystem:
    """Tests for SensorySystem and catalog."""

    def test_dual_cppn_has_sensory_system(self, representation):
        """DualCPPN declares a sensory_system with inputs and outputs."""
        env = representation.sensory_system
        assert len(env.inputs) > 0
        assert len(env.outputs) > 0
        ids = env.input_ids()
        assert "x" in ids
        assert "bias" in ids

    def test_dual_cppn_env_has_categories(self, representation):
        """DualCPPN sensory_system has spatial and interaction categories."""
        env = representation.sensory_system
        assert env.has_category("spatial")
        assert env.has_category("interaction")

    def test_dual_cppn_env_has_derived(self, representation):
        """DualCPPN sensory_system has derived inputs (distance)."""
        env = representation.sensory_system
        assert len(env.derived_inputs) > 0
        assert env.derived_inputs[0].id == "distance"

    def test_conway_has_interaction_signals(self):
        """Conway representation declares interaction signals."""
        from eyecatcher.representation.ca import ConwayRepresentation

        ca = ConwayRepresentation()
        env = ca.sensory_system
        assert env.has_signal("mouse_x")
        assert env.has_signal("mouse_y")
        assert env.has_category("interaction")

    def test_conway_env_no_outputs(self):
        """Conway representation currently declares no output signals."""
        from eyecatcher.representation.ca import ConwayRepresentation

        ca = ConwayRepresentation()
        assert len(ca.sensory_system.outputs) == 0

    def test_catalog_presets_consistent(self):
        """Catalog convenience presets have expected lengths and ids."""
        assert len(catalog.DUAL_CPPN_VISUAL_INPUTS) == 10
        assert len(catalog.DUAL_CPPN_TIME_INPUTS) == 5
        ids = [s.id for s in catalog.DUAL_CPPN_VISUAL_INPUTS]
        assert "x" in ids and "y" in ids and "bias" in ids

    def test_export_for_frontend_with_env(self, representation):
        """export_for_frontend(env) returns SIGNAL_GROUPS and TOGGLEABLE_SIGNALS."""
        data = export_for_frontend(representation.sensory_system)
        assert "SIGNAL_GROUPS" in data
        assert "TOGGLEABLE_SIGNALS" in data
        assert "SIGNAL_IDS" in data
        groups = data["SIGNAL_GROUPS"]
        assert any(
            g.get("label") in ("Spatial", "Temporal", "Interaction") for g in groups
        )

    def test_sensory_system_has_signal(self):
        """SensorySystem.has_signal works for present and absent signals."""
        from eyecatcher.signals.receptor import Receptor
        from eyecatcher.signals.sensory_system import SensorySystem, Signal

        rec = Receptor("test", inputs=(Signal("a", "A"), Signal("b", "B")))
        env = SensorySystem(receptors=(rec,), outputs=())
        assert env.has_signal("a")
        assert not env.has_signal("c")
