"""Tests for genome JSON serialization round-trip."""
import pytest

from eyecatcher.cppn_engine import CPPNEngine, create_random_dual_genome
from eyecatcher.genome_serialization import (
    dual_genome_to_json,
    dual_genome_from_json,
)


def test_dual_genome_round_trip():
    """Serializing a dual genome and deserializing yields equivalent structure."""
    engine = CPPNEngine()
    engine.create_population()
    dual = create_random_dual_genome(engine, genome_id=7)
    data = dual_genome_to_json(dual)
    assert "key" in data
    assert data["key"] == 7
    assert "visual" in data
    assert "time_signal" in data
    assert "nodes" in data["visual"]
    assert "connections" in data["visual"]

    restored = dual_genome_from_json(data, engine)
    assert restored.key == dual.key
    assert len(restored.visual.nodes) == len(dual.visual.nodes)
    assert len(restored.visual.connections) == len(dual.visual.connections)
    assert len(restored.time_signal.nodes) == len(dual.time_signal.nodes)


def test_dual_genome_round_trip_query_consistency():
    """After round-trip, querying the CPPN gives same-shaped output."""
    engine = CPPNEngine()
    engine.create_population()
    dual = create_random_dual_genome(engine, genome_id=0)
    data = dual_genome_to_json(dual)
    restored = dual_genome_from_json(data, engine)

    r0, g0, b0 = engine.query_dual_cppn(dual, 0.5, 0.5, raw_time=0.3)
    r1, g1, b1 = engine.query_dual_cppn(restored, 0.5, 0.5, raw_time=0.3)
    assert isinstance(r0, (int, float)) and isinstance(r1, (int, float))
    assert 0 <= r0 <= 255 and 0 <= r1 <= 255
    assert 0 <= g0 <= 255 and 0 <= g1 <= 255
    assert 0 <= b0 <= 255 and 0 <= b1 <= 255
