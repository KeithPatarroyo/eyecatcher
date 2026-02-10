"""Tests for signal registry and frontend/backend config alignment."""

import os
import re

import pytest
from eyecatcher import get_root_dir
from eyecatcher.evolution import CPPNEngine
from eyecatcher.evolution.signals import (
    TIME_INPUTS,
    TIME_OUTPUTS,
    VISUAL_INPUTS,
    VISUAL_OUTPUTS,
)


def test_neat_config_matches_registry():
    """NEAT config num_inputs/num_outputs match registry (validated at engine init)."""
    engine = CPPNEngine()
    assert engine.config.genome_config.num_inputs == len(VISUAL_INPUTS)
    assert engine.config.genome_config.num_outputs == len(VISUAL_OUTPUTS)
    assert engine.time_config.genome_config.num_inputs == len(TIME_INPUTS)
    assert engine.time_config.genome_config.num_outputs == len(TIME_OUTPUTS)


def test_frontend_signals_match_backend():
    """JS evolution_config.js SIGNALS match Python registry (toggleable inputs)."""
    root = get_root_dir()
    js_path = os.path.join(root, "static", "js", "modules", "evolution_config.js")
    if not os.path.isfile(js_path):
        pytest.skip("evolution_config.js not found")
    with open(js_path, encoding="utf-8") as f:
        text = f.read()

    # Python: toggleable = those with non-empty enable_key (exclude spatial and bias)
    time_toggleable = [s.enable_key for s in TIME_INPUTS if s.enable_key]
    visual_toggleable = [s.enable_key for s in VISUAL_INPUTS if s.enable_key]

    # JS: extract enableKey values in order (time inputs first, then visual inputs)
    all_enable_keys = re.findall(r'enableKey:\s*["\']([^"\']+)["\']', text)
    # SIGNALS has time.inputs (4) then visual.inputs (4)
    n_time = len(time_toggleable)
    n_visual = len(visual_toggleable)
    if len(all_enable_keys) < n_time + n_visual:
        pytest.fail(
            f"evolution_config.js has {len(all_enable_keys)} enableKey entries, "
            f"expected {n_time + n_visual}"
        )
    js_time = all_enable_keys[:n_time]
    js_visual = all_enable_keys[n_time : n_time + n_visual]

    assert len(js_time) == len(
        time_toggleable
    ), f"Time inputs: JS has {len(js_time)}, Python has {len(time_toggleable)}"
    assert len(js_visual) == len(
        visual_toggleable
    ), f"Visual inputs: JS has {len(js_visual)}, Python has {len(visual_toggleable)}"
    # Python enable_key is camelCase in registry (matches JS enableKey)
    assert (
        js_time == time_toggleable
    ), f"Time enableKeys: JS {js_time} vs Python {time_toggleable}"
    assert (
        js_visual == visual_toggleable
    ), f"Visual enableKeys: JS {js_visual} vs Python {visual_toggleable}"
