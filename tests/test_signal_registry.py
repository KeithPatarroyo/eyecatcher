"""Tests for signal registry and frontend/backend config alignment."""

import json
import os

import pytest
from eyecatcher import get_root_dir
from eyecatcher.signals import (
    TIME_INPUTS,
    TIME_OUTPUTS,
    VISUAL_INPUTS,
    VISUAL_OUTPUTS,
    export_for_frontend,
)
from eyecatcher.signals.signals import _is_toggleable


def test_neat_config_matches_registry(cppn_engine):
    """NEAT config num_inputs/num_outputs match registry (validated at engine init)."""
    assert cppn_engine.config.genome_config.num_inputs == len(VISUAL_INPUTS)
    assert cppn_engine.config.genome_config.num_outputs == len(VISUAL_OUTPUTS)
    assert cppn_engine.time_config.genome_config.num_inputs == len(TIME_INPUTS)
    assert cppn_engine.time_config.genome_config.num_outputs == len(TIME_OUTPUTS)


def test_signals_export_for_frontend():
    """export_for_frontend() returns SIGNAL_TOGGLES, OUTPUTS, SIGNAL_IDS."""
    data = export_for_frontend()
    assert "SIGNAL_TOGGLES" in data
    assert "OUTPUTS" in data
    assert "SIGNAL_IDS" in data
    assert list(data["SIGNAL_TOGGLES"].keys()) == ["time", "visual"]
    for cppn_type in ("time", "visual"):
        assert "toggleableInputs" in data["SIGNAL_TOGGLES"][cppn_type]
        for inp in data["SIGNAL_TOGGLES"][cppn_type]["toggleableInputs"]:
            assert "id" in inp and "label" in inp
    assert data["OUTPUTS"]["visual"] == [
        {"id": "red", "label": "Red"},
        {"id": "green", "label": "Green"},
        {"id": "blue", "label": "Blue"},
    ]
    assert data["OUTPUTS"]["time"] == [{"id": "output", "label": "Modified Time"}]
    assert set(data["SIGNAL_IDS"]) == {
        "activity",
        "mouse_dist",
        "mouse_speed",
        "raw_time",
    }


def test_frontend_signals_match_backend():
    """Generated evolution_config_signals.generated.js matches Python registry."""
    root = get_root_dir()
    js_path = os.path.join(
        root, "static", "js", "evolution", "evolution_config_signals.generated.js"
    )
    if not os.path.isfile(js_path):
        pytest.skip("run make generate-signals to create generated file")
    with open(js_path, encoding="utf-8") as f:
        text = f.read()

    # Extract JSON from window.EvolutionConfigSignals = { ... };
    start = text.find("window.EvolutionConfigSignals = ")
    assert start >= 0, "Generated file should assign EvolutionConfigSignals"
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
    data = json.loads(text[start : end + 1])

    time_toggleable = [s.id for s in TIME_INPUTS if _is_toggleable(s)]
    visual_toggleable = [s.id for s in VISUAL_INPUTS if _is_toggleable(s)]

    toggles = data["SIGNAL_TOGGLES"]
    js_time = [t["id"] for t in toggles["time"]["toggleableInputs"]]
    js_visual = [t["id"] for t in toggles["visual"]["toggleableInputs"]]

    assert js_time == time_toggleable, f"Time: JS {js_time} vs Python {time_toggleable}"
    assert (
        js_visual == visual_toggleable
    ), f"Visual ids: JS {js_visual} vs Python {visual_toggleable}"
